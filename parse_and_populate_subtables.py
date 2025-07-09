import json
import mysql.connector
from mysql.connector import Error
import hashlib
import re
from typing import Dict, List, Any, Set
import requests
import os # For schema file operations

# --- Configuration (Should match or be loaded consistently) ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Ec2024_12',
    'database': 'rsk_mail'
}

MYSQL_MAX_TABLE_NAME_LENGTH = 64
TABLE_PREFIX = "ods_"
MASTER_TABLE_BASE_NAME = "api_response_items"
SCHEMA_CACHE_DIR = "generated_schemas" # Directory to store/load schema files

INTERFACE_DICT = {
    "1049": ("credit_ratings", "企业信用评级"),
    "884": ("tax_ratings", "税务评级"),
    "1001": ("base_info", "工商信息"),
    "1163": ("person_legal_proceedings", "法律诉讼(人员)"),
    "9999": ("a_very_long_interface_name_for_testing_abbreviation_rules", "超长接口名称测试缩写规则")
}

TYPE_MAP_PARSER = {
    "String": "VARCHAR(255)", "Number": "BIGINT", "Boolean": "BOOLEAN",
    "Date": "DATE", "Object": "JSON", "Array": "JSON"
}

# --- Helper Functions (Replicated/Adapted from apijsontosql4.py) ---
def to_snake_case_parser(name: str) -> str:
    name = re.sub(r'([a-z\d])([A-Z])', r'\1_\2', name)
    return name.replace("__", "_").lower()

def shorten_table_name_parser(name: str, max_length: int = MYSQL_MAX_TABLE_NAME_LENGTH) -> str:
    if len(name) <= max_length: return name
    prefix_len = len(TABLE_PREFIX)
    core_name = name[prefix_len:]
    max_core_len = max_length - prefix_len
    if len(core_name) <= max_core_len: return name
    name_hash = hashlib.md5(core_name.encode('utf-8')).hexdigest()[:5]
    hash_len = len(name_hash) + 1
    available_len_for_core = max_core_len - hash_len
    if available_len_for_core <= 0:
        return TABLE_PREFIX + core_name[:max_core_len - len(name_hash)] + name_hash
    truncated_core = core_name[:available_len_for_core]
    return f"{TABLE_PREFIX}{truncated_core}_{name_hash}"[:max_length]

def get_full_table_name_parser(base_name_without_prefix: str) -> str:
    prefixed_name = TABLE_PREFIX + base_name_without_prefix
    return shorten_table_name_parser(prefixed_name)

ACTUAL_MASTER_TABLE_NAME = get_full_table_name_parser(MASTER_TABLE_BASE_NAME)

def get_detail_table_base_name_parser(interface_table_prefix: str, path: List[str]) -> str:
    effective_path = [p for p in path if p != '_child']
    if not effective_path:
         return to_snake_case_parser(f"{interface_table_prefix}_detail")
    return to_snake_case_parser(f"{interface_table_prefix}_{'_'.join(effective_path)}_detail")

# --- Schema Fetching (Reads from file cache, falls back to live API, caches new) ---
def fetch_api_schema_from_source_parser(api_id: str) -> Dict | None:
    """
    Fetches API schema: tries local cache file first, then live API, and caches if fetched live.
    """
    schema_file_path = os.path.join(SCHEMA_CACHE_DIR, f"{api_id}.json")

    # 1. Try to load from local cache file
    if os.path.exists(schema_file_path):
        try:
            with open(schema_file_path, 'r', encoding='utf-8') as f_schema:
                schema = json.load(f_schema)
            print(f"  [解析器信息] API ID {api_id} 的Schema已从缓存文件加载: {schema_file_path}")
            return schema
        except (IOError, json.JSONDecodeError) as e:
            print(f"  [解析器警告] 从缓存文件 {schema_file_path} 加载Schema失败: {e}。将尝试从实时API获取。", file=sys.stderr)

    # 2. Fallback: Fetch from live API (logic copied from apijsontosql4.py)
    print(f"  [解析器信息] 缓存未命中或加载失败，正在从真实接口获取API ID {api_id} 的Schema...")
    url = f"https://open.tianyancha.com/open-admin/interface/uni.json?id={api_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
        "Referer": "https://open.tianyancha.com/",
    }
    live_schema = None
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("data", {})
        return_param_str = data.get("returnParam")
        if not return_param_str:
            print(f"  [解析器警告] API ID {api_id} 的响应中未找到 'returnParam' 字段 (实时获取)。", file=sys.stderr)
            return None

        return_param_dict = json.loads(return_param_str)
        result_node = return_param_dict.get("result", {})
        if not result_node or not isinstance(result_node, dict):
            print(f"  [解析器警告] API ID {api_id} 的 'result' 节点无效或缺失 (实时获取)。", file=sys.stderr)
            return None

        # Path finding logic (same as in apijsontosql4.py)
        items_node_direct = result_node.get("items")
        if items_node_direct and isinstance(items_node_direct, dict) and items_node_direct.get("type") == "Array":
            # ... (Path 1 logic)
            items_structure = items_node_direct.get("_")
            if items_structure and isinstance(items_structure, dict):
                child_node = items_structure.get("_child")
                if child_node and isinstance(child_node, dict) and child_node.get("type") == "Object":
                    child_fields = child_node.get("_")
                    if child_fields and isinstance(child_fields, dict):
                        print(f"  [解析器信息] API {api_id}: 使用 result.items._._child._ 结构 (实时获取)。")
                        live_schema = child_fields

        if not live_schema:
            result_underscore_node = result_node.get("_")
            if result_underscore_node and isinstance(result_underscore_node, dict):
                items_node_nested = result_underscore_node.get("items")
                if items_node_nested and isinstance(items_node_nested, dict) and items_node_nested.get("type") == "Array":
                    # ... (Path 2 logic)
                    items_structure = items_node_nested.get("_")
                    if items_structure and isinstance(items_structure, dict):
                        child_node = items_structure.get("_child")
                        if child_node and isinstance(child_node, dict) and child_node.get("type") == "Object":
                            child_fields = child_node.get("_")
                            if child_fields and isinstance(child_fields, dict):
                                print(f"  [解析器信息] API {api_id}: 使用 result._.items._._child._ 结构 (实时获取)。")
                                live_schema = child_fields

                if not live_schema and not items_node_nested:
                    # ... (Path 3 logic)
                    is_not_wrapper = not ('total' in result_underscore_node and 'items' in result_underscore_node)
                    is_schema_like = all(isinstance(v, dict) and "type" in v for v in result_underscore_node.values())
                    if is_not_wrapper and is_schema_like and result_underscore_node:
                        print(f"  [解析器信息] API {api_id}: 使用 result._ 结构 (实时获取)。")
                        live_schema = result_underscore_node

            if not live_schema and result_underscore_node and isinstance(result_underscore_node, str):
                # ... (Path 4 logic)
                try:
                    parsed_schema_from_string = json.loads(result_underscore_node)
                    print(f"  [解析器信息] API {api_id}: 解析 result._ 字符串结构 (实时获取)。")
                    live_schema = parsed_schema_from_string
                except json.JSONDecodeError:
                    print(f"  [解析器错误] API {api_id}: result._ 字符串无法被解析为JSON (实时获取)。", file=sys.stderr)

        if not live_schema and not items_node_direct and not result_underscore_node and \
           all(isinstance(v, dict) and "type" in v for v in result_node.values()) and result_node:
            # ... (Path 5 logic)
            print(f"  [解析器信息] API {api_id}: 使用 result 本身作为 schema (实时获取)。")
            live_schema = result_node

        if not live_schema:
            print(f"  [解析器警告] API ID {api_id} 未能从实时接口定位到 'row_content' 的详细字段定义。", file=sys.stderr)
            return None

    except requests.exceptions.RequestException as e:
        print(f"  [解析器错误] 请求API ID {api_id} 的schema时发生网络错误 (实时获取): {e}", file=sys.stderr)
        return None
    except (ValueError, json.JSONDecodeError) as e:
        print(f"  [解析器错误] 处理API ID {api_id} 的schema数据时发生错误 (实时获取): {e}", file=sys.stderr)
        return None

    # 3. Cache the newly fetched schema (if successful)
    if live_schema:
        try:
            os.makedirs(SCHEMA_CACHE_DIR, exist_ok=True)
            with open(schema_file_path, 'w', encoding='utf-8') as f_schema:
                json.dump(live_schema, f_schema, ensure_ascii=False, indent=4)
            print(f"  [解析器信息] API ID {api_id} 的实时获取的schema已缓存到: {schema_file_path}")
        except (IOError, OSError) as e:
            print(f"  [解析器警告] 缓存实时获取的schema到 {schema_file_path} 失败: {e}", file=sys.stderr)

    return live_schema

# --- Database and Core Logic ---
# ... (create_db_connection_parser, _insert_row, populate_table_and_children_recursive, parse_and_insert_row_content, main)
# ... The rest of the file remains the same as the v7 version (feat/implement-recursive-subtable-population)
# ... For brevity, only the fetch_api_schema_from_source_parser is shown fully modified.
# ... The following is a truncated version of the rest of the file for context.

def create_db_connection_parser():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected(): print("数据库连接成功 (parser)。")
        return connection
    except Error as e:
        print(f"数据库连接失败 (parser): {e}")
    return None

def _insert_row(cursor, table_name: str, data_dict: Dict[str, Any]) -> int | None:
    if not data_dict:
        # print(f"    [信息] 表 {table_name} 无简单/JSON字段数据可插入。") # Can be too verbose
        return None

    columns = list(data_dict.keys())
    placeholders = ['%s'] * len(columns)
    sql = f"INSERT INTO `{table_name}` ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
    try:
        cursor.execute(sql, list(data_dict.values()))
        return cursor.lastrowid
    except Error as e:
        print(f"    - [数据库错误] 插入到表 `{table_name}` 失败: {e}")
        print(f"      - SQL: {sql}")
        print(f"      - Data: {str(data_dict)[:500]}...")
        raise

def populate_table_and_children_recursive(
    cursor,
    current_data: Any,
    current_schema: Dict[str, Any],
    target_table_name: str,
    fk_to_parent_column_name: str | None,
    parent_tid_value: int | None,
    original_interface_prefix: str, # Added: The root prefix for the API interface (e.g., "base_info")
    current_field_path: List[str]    # Added: The path of keys from root of row_content to current_data
):
    if isinstance(current_data, list):
        # If current_data is a list, it means we are processing items of an array field from the parent.
        # The current_schema should be the schema for *each item* in this list.
        # The target_table_name is the table where these list items should be stored.
        for item_data in current_data:
            if not isinstance(item_data, dict):
                print(f"  [警告] 列表中的项目不是字典，跳过: {str(item_data)[:100]} (目标表: {target_table_name})")
                continue
            # Each item is processed as a new row in the target_table_name,
            # using the same schema, parent FK, and path context.
            # The original_interface_prefix remains the same. current_field_path also refers to the list field itself.
            populate_table_and_children_recursive(
                cursor, item_data, current_schema,
                target_table_name, fk_to_parent_column_name, parent_tid_value,
                original_interface_prefix, current_field_path
            )
        return

    if not isinstance(current_data, dict):
        print(f"  [警告] 当前数据不是字典，无法处理: {str(current_data)[:100]} (目标表: {target_table_name})")
        return

    simple_fields_for_current_row = {}
    if fk_to_parent_column_name and parent_tid_value is not None:
        simple_fields_for_current_row[fk_to_parent_column_name] = parent_tid_value

    children_to_process_later = []

    for api_field_key, api_field_value in current_data.items():
        db_col_name = to_snake_case_parser(api_field_key)
        field_schema = current_schema.get(api_field_key)

        if not field_schema:
            # print(f"  [警告] 字段 '{api_field_key}' 在提供的schema中未找到定义，跳过。 (目标表: {target_table_name})") # Can be too verbose
            continue

        field_type = field_schema.get("type")

        if field_type == "Object" and "_" in field_schema:
            if api_field_value is not None:
                # Child's path is current path + this field's key
                child_field_path = current_field_path + [api_field_key]
                # Use original_interface_prefix and the new accumulated path for child table name
                child_table_base_name = get_detail_table_base_name_parser(original_interface_prefix, child_field_path)
                child_table_full_name = get_full_table_name_parser(child_table_base_name)

                fk_in_child_col_name = f"{to_snake_case_parser(target_table_name)}_tid" # FK in child points to current table's tid

                children_to_process_later.append({
                    "data": api_field_value,
                    "schema": field_schema["_"],
                    "table_name": child_table_full_name,
                    "fk_col": fk_in_child_col_name,
                    "original_interface_prefix": original_interface_prefix, # Pass down root prefix
                    "field_path": child_field_path # Pass down accumulated path
                })
                # Logic for also storing as JSON in parent (if applicable based on apijsontosql4's rules)
                if target_table_name == get_full_table_name_parser(get_detail_table_base_name_parser(original_interface_prefix, [])): # If current table is the first-level detail table
                    # This condition needs to be more robust or rely on apijsontosql4's output for which fields are JSON in parent
                    # Example: For base_info, specific objects are also JSON in parent.
                    if original_interface_prefix == "base_info" and db_col_name in ('liquidating_info', 'headquarters', 'brief_cancel'):
                         simple_fields_for_current_row[db_col_name] = json.dumps(api_field_value, ensure_ascii=False) if api_field_value else None

        elif field_type == "Array" and "_" in field_schema and "_child" in field_schema["_"] and \
             isinstance(field_schema["_"]["_child"], dict) and "_" in field_schema["_"]["_child"]:
            if api_field_value is not None and isinstance(api_field_value, list) and api_field_value:
                child_item_schema = field_schema["_"]["_child"]["_"]
                child_field_path = current_field_path + [api_field_key]
                child_table_base_name = get_detail_table_base_name_parser(original_interface_prefix, child_field_path)
                child_table_full_name = get_full_table_name_parser(child_table_base_name)
                fk_in_child_col_name = f"{to_snake_case_parser(target_table_name)}_tid"

                children_to_process_later.append({
                    "data": api_field_value, # This is the list of items
                    "schema": child_item_schema, # Schema for each item in the list
                    "table_name": child_table_full_name,
                    "fk_col": fk_in_child_col_name,
                    "is_list_of_items": True, # Flag that data is a list
                    "original_interface_prefix": original_interface_prefix,
                    "field_path": child_field_path
                })
        else:
            # Simple type, or Object/Array to be stored as JSON string directly in this table
            # (because schema doesn't have "_" or "_._child._" indicating further structure for separate tables)
            processed_value = api_field_value
            processed_value = api_field_value
            notice_str = field_schema.get("notice", "")
            meta_api_type = field_schema.get("type") # "String", "Number", "Boolean", "Date", "Object", "Array"
            db_sql_type, _ = parse_notice_for_type_length(notice_str)

            # Step 1: Handle Empty/Whitespace Strings
            if isinstance(processed_value, str) and not processed_value.strip():
                is_target_non_textual_for_empty = False
                if db_sql_type:
                    if db_sql_type.upper() not in ["VARCHAR", "CHAR", "TEXT", "TINYTEXT", "MEDIUMTEXT", "LONGTEXT"]:
                        is_target_non_textual_for_empty = True
                elif meta_api_type in ["Number", "Boolean", "Date"]:
                    is_target_non_textual_for_empty = True

                if is_target_non_textual_for_empty:
                    print(f"    - [数据转换] 字段 '{api_field_key}' (列: {db_col_name}) 值为空白字符串，目标类型非纯文本，将转换为NULL。Notice: '{notice_str}', MetaType: '{meta_api_type}'")
                    processed_value = None
                # else: processed_value remains '', which is fine for text types.

            # Step 2: Handle Percentage Strings (if processed_value is still a string and not None)
            if isinstance(processed_value, str) and processed_value.endswith('%'):
                is_target_numeric_for_percent = False
                if db_sql_type:
                    if db_sql_type.upper() in ["DECIMAL", "NUMERIC", "FLOAT", "DOUBLE", "INT", "INTEGER", "BIGINT", "TINYINT", "SMALLINT", "MEDIUMINT"]:
                        is_target_numeric_for_percent = True
                elif meta_api_type == "Number": # Fallback if notice didn't specify a numeric SQL type
                    is_target_numeric_for_percent = True

                if is_target_numeric_for_percent:
                    try:
                        # Remove '%' and any potential thousands separators (like comma)
                        cleaned_val_str = processed_value.rstrip('%').replace(',', '')
                        # Convert to float. Database will handle further conversion to DECIMAL/INT.
                        # If data is like "4.17%" -> 4.17
                        # If data is like "0.05%" (meaning 0.0005), this simple replace is not enough.
                        # Assuming "X%" means X, not X/100, for now.
                        # If "X%" actually means X/100, then: float(cleaned_val_str) / 100.0
                        processed_value = float(cleaned_val_str)
                        print(f"    - [数据转换] 字段 '{api_field_key}' (列: {db_col_name}) 百分比值 '{api_field_value}' 转换为数字: {processed_value}")
                    except ValueError:
                        print(f"    - [数据转换警告] 字段 '{api_field_key}' (列: {db_col_name}) 百分比值 '{api_field_value}' 无法转换为有效数字，将设为NULL。")
                        processed_value = None

            # Assign to row after all processing for this simple field
            # Note: field_type here is from the API schema's "type" (String, Number, Object, Array)
            # It determines if json.dumps is needed for Object/Array types that are NOT being turned into child tables.
            if field_type == "Object" or field_type == "Array":
                # This case applies if the schema says it's an Object/Array but there's no "_" structure
                # indicating it should be a child table. So, it's stored as JSON in the current table.
                simple_fields_for_current_row[db_col_name] = json.dumps(processed_value, ensure_ascii=False) if processed_value is not None else None
            else: # String, Number, Boolean, Date from schema (after our specific value processing)
                simple_fields_for_current_row[db_col_name] = processed_value

    current_row_tid = _insert_row(cursor, target_table_name, simple_fields_for_current_row)
    if current_row_tid is None:
        # Check if simple_fields_for_current_row actually had data fields beyond a possible FK
        data_fields_count = 0
        for k,v_ in simple_fields_for_current_row.items():
            if k != fk_to_parent_column_name:
                data_fields_count +=1

        if data_fields_count > 0 : # If there were actual data fields to insert for this row
            raise Error(f"Insert into {target_table_name} (with data fields) failed to return a TID.")
        else: # No actual data fields, or only FK, so no row was (or needed to be) inserted. No children.
            # This means current_data was empty or only contained complex types that will be handled by children_to_process_later
            # but no simple fields for *this* table row itself.
            # print(f"    [信息] 表 {target_table_name} 没有简单/JSON字段插入，但可能有子表待处理。")
            # We need a TID if there are children. If an object is just a container for other lists/objects
            # and has no simple fields itself, apijsontosql4.py might not even create a parent row for it,
            # or it creates a row with just FK. This needs consistent handling.
            # For now, if _insert_row returns None, we assume no row was inserted, so no children can be linked from it.
            return

    for child_task in children_to_process_later:
        child_data = child_task["data"]
        child_schema = child_task["schema"]
        child_table_name = child_task["table_name"]
        fk_col_in_child = child_task["fk_col"]
        # Pass down original_interface_prefix and the child's specific field_path
        child_original_interface_prefix = child_task["original_interface_prefix"]
        child_field_path = child_task["field_path"]

        if child_task.get("is_list_of_items", False):
            for item_in_list in child_data:
                 populate_table_and_children_recursive(
                     cursor, item_in_list, child_schema,
                     child_table_name, fk_col_in_child, current_row_tid,
                     child_original_interface_prefix, child_field_path # Pass context
                 )
        else:
            populate_table_and_children_recursive(
                cursor, child_data, child_schema,
                child_table_name, fk_col_in_child, current_row_tid,
                child_original_interface_prefix, child_field_path # Pass context
            )

def parse_and_insert_row_content(cursor, master_item_tid: int, interface_id: int, raw_json_content: str, interface_dict: Dict):
    # ... (logic to determine actual_business_data from raw_json_content - remains same as v7)
    print(f"\n开始处理主表TID: {master_item_tid}, 接口ID: {interface_id}")
    if not raw_json_content:
        print(f"  - raw_row_content 为空，无需解析。")
        return

    try:
        parsed_json = json.loads(raw_json_content)
    except json.JSONDecodeError as e:
        print(f"  - JSON解析错误 for master_item_tid {master_item_tid}: {e}")
        return

    actual_business_data = None
    if isinstance(parsed_json, dict) and 'result' in parsed_json and ('reason' in parsed_json or 'error_code' in parsed_json):
        is_successful_wrapper = parsed_json.get('reason') == 'ok' or parsed_json.get('error_code') == 0
        if is_successful_wrapper:
            actual_business_data = parsed_json.get('result')
            if actual_business_data is None:
                print(f"  - [信息] raw_json 是带包装结构且成功，但 'result' 内容为null。TID: {master_item_tid}。无业务数据可处理。")
                return
            print(f"  - 检测到外层包装JSON，提取 'result' 节点内容进行处理。TID: {master_item_tid}")
        else:
            error_info = parsed_json.get('reason', f"error_code: {parsed_json.get('error_code')}")
            print(f"  - [警告] raw_json 是带包装结构但表示失败/错误: '{error_info}'. TID: {master_item_tid}。跳过处理。")
            return
    elif isinstance(parsed_json, (dict, list)):
        actual_business_data = parsed_json
        print(f"  - raw_json 被解析为直接的业务数据（字典或列表）。TID: {master_item_tid}")
    else:
        print(f"  - [错误] 解析后的raw_json既不是预期的包装结构也不是字典/列表。类型: {type(parsed_json)}，TID: {master_item_tid}。跳过处理。")
        return

    if actual_business_data is None:
        print(f"  - [信息] 最终业务数据为None，TID: {master_item_tid}。无业务数据可处理。")
        return
    if isinstance(actual_business_data, list) and not actual_business_data:
        print(f"  - [信息] 最终业务数据为空列表，TID: {master_item_tid}。populate_table_and_children_recursive 将处理此情况。")
    elif not isinstance(actual_business_data, (dict, list)):
        print(f"  - [错误] 最终业务数据既不是字典也不是列表。类型: {type(actual_business_data)}，TID: {master_item_tid}。跳过处理。")
        return

    interface_id_str = str(interface_id)
    if interface_id_str not in interface_dict:
        print(f"  - 未知的 interface_id: {interface_id}，无法在INTERFACE_DICT中找到配置。")
        return

    interface_config = interface_dict[interface_id_str]
    interface_table_prefix = interface_config[0]

    api_specific_row_content_schema = fetch_api_schema_from_source_parser(interface_id_str) # Now uses caching/live fetch
    if not api_specific_row_content_schema:
        print(f"  - 无法获取API ID {interface_id_str}的schema，跳过子表填充。")
        return

    first_level_detail_table_base = get_detail_table_base_name_parser(interface_table_prefix, [])
    first_level_detail_table_full = get_full_table_name_parser(first_level_detail_table_base)
    fk_to_master_column = f"{to_snake_case_parser(ACTUAL_MASTER_TABLE_NAME)}_tid"

    populate_table_and_children_recursive(
        cursor,
        current_data=actual_business_data,
        current_schema=api_specific_row_content_schema,
        target_table_name=first_level_detail_table_full,
        fk_to_parent_column_name=fk_to_master_column,
        parent_tid_value=master_item_tid,
        original_interface_prefix=interface_table_prefix, # Pass the root interface prefix
        current_field_path=[] # Initial path is empty for the top-level row_content
    )
    print(f"  - 完成主表TID: {master_item_tid} 的子表处理。")

def main():
    # ... (main function remains largely the same as v7, uses the updated fetch_api_schema_from_source_parser)
    print("开始解析 ods_api_response_items 中的 raw_row_content 并填充子表 (增强版, 带schema缓存)...")
    connection = create_db_connection_parser()
    if not connection: return

    cursor = None
    current_processing_tid = None
    try:
        cursor = connection.cursor(dictionary=True)
        query = f"SELECT tid, interface_id, raw_row_content FROM `{ACTUAL_MASTER_TABLE_NAME}` WHERE raw_row_content IS NOT NULL AND is_row_content_processed = FALSE"

        cursor.execute(query)
        items_to_process = cursor.fetchall()
        print(f"找到 {len(items_to_process)} 条待处理记录。")

        for item in items_to_process:
            current_processing_tid = item['tid']
            master_tid = item['tid']
            interface_id = item['interface_id']
            raw_json = item['raw_row_content']

            print(f"--- 开始处理主记录 TID: {master_tid} ---")
            cursor.execute("START TRANSACTION;")
            print(f"  - 事务开始 for TID: {master_tid}")

            parse_and_insert_row_content(cursor, master_tid, interface_id, raw_json, INTERFACE_DICT)

            update_sql = f"UPDATE `{ACTUAL_MASTER_TABLE_NAME}` SET is_row_content_processed = TRUE WHERE tid = %s"
            cursor.execute(update_sql, (master_tid,))
            print(f"  - 标记主记录 TID {master_tid} 为已处理。")

            cursor.execute("COMMIT;")
            print(f"  - 事务提交 for TID: {master_tid}")
            print(f"--- 完成处理主记录 TID: {master_tid} ---")

    except Error as e:
        print(f"处理主表数据时发生数据库错误 (当前处理TID: {current_processing_tid if current_processing_tid else 'N/A'}): {e}")
        if connection and connection.is_connected() and cursor:
            print("  - 正在回滚当前事务...")
            cursor.execute("ROLLBACK;")
            print("  - 事务已回滚。")
    except Exception as ex:
        print(f"处理过程中发生非数据库错误 (当前处理TID: {current_processing_tid if current_processing_tid else 'N/A'}): {ex}")
        import traceback
        traceback.print_exc()
        if connection and connection.is_connected() and cursor:
            print("  - 正在回滚当前事务 (因非数据库错误)...")
            cursor.execute("ROLLBACK;")
            print("  - 事务已回滚。")
    finally:
        if connection and connection.is_connected():
            if cursor: cursor.close()
            connection.close()
            print("\n数据库连接已关闭 (parser)。")

if __name__ == "__main__":
    # Ensure SCHEMA_CACHE_DIR exists, or at least the script attempts to create it.
    # The fetch function itself will try to create it if it writes a new cache file.
    # os.makedirs(SCHEMA_CACHE_DIR, exist_ok=True) # Can be done here or within fetch

    if DB_CONFIG.get('user') == 'your_username':
        print("[警告] 请在脚本顶部更新您的 `DB_CONFIG` (parser) 数据库连接信息！")
    else:
        main()
        print("\n--- 子表填充过程执行完毕 ---")
        print("请注意：此脚本实现了基于schema的递归子表填充，并尝试从文件缓存加载schema，回退到实时API。")

```
