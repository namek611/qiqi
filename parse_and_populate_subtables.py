import json
import mysql.connector
from mysql.connector import Error
import hashlib
import re
from typing import Dict, List, Any, Set
import requests # Added for live schema fetching

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

# --- Schema Fetching (Copied and adapted from apijsontosql4.py) ---
def fetch_api_schema_from_source_parser(api_id: str, mock_schemas: Dict = None) -> Dict | None:
    """
    Fetches the API schema structure from the Tianyancha source.
    This is a direct copy/adaptation of the logic from apijsontosql4.py's
    `fetch_api_schema_from_source` function.
    `mock_schemas` can be used for testing IF live calls are disabled.
    """
    if mock_schemas and api_id in mock_schemas:
        print(f"  [解析器信息] 使用API ID {api_id} 的Mock Schema。")
        return mock_schemas[api_id]

    url = f"https://open.tianyancha.com/open-admin/interface/uni.json?id={api_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
        "Referer": "https://open.tianyancha.com/",
    }
    try:
        print(f"  [解析器信息] 正在从真实接口获取API ID {api_id} 的Schema: {url}")
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("data", {})
        return_param_str = data.get("returnParam")
        if not return_param_str:
            print(f"  [解析器警告] API ID {api_id} 的响应中未找到 'returnParam' 字段。", file=sys.stderr)
            return None

        return_param_dict = json.loads(return_param_str)
        result_node = return_param_dict.get("result", {})
        if not result_node or not isinstance(result_node, dict):
            print(f"  [解析器警告] API ID {api_id} 的 'result' 节点无效或缺失。", file=sys.stderr)
            return None

        # Path 1: Standard list items directly under result (e.g., result.items._._child._)
        items_node_direct = result_node.get("items")
        if items_node_direct and isinstance(items_node_direct, dict) and items_node_direct.get("type") == "Array":
            items_structure = items_node_direct.get("_")
            if items_structure and isinstance(items_structure, dict):
                child_node = items_structure.get("_child")
                if child_node and isinstance(child_node, dict) and child_node.get("type") == "Object":
                    child_fields = child_node.get("_")
                    if child_fields and isinstance(child_fields, dict):
                        print(f"  [解析器信息] API {api_id}: 使用 result.items._._child._ 结构作为 row_content 的schema。")
                        return child_fields

        # Path 2: Items nested under result._ (e.g., result._.items._._child._)
        result_underscore_node = result_node.get("_")
        if result_underscore_node and isinstance(result_underscore_node, dict):
            items_node_nested = result_underscore_node.get("items")
            if items_node_nested and isinstance(items_node_nested, dict) and items_node_nested.get("type") == "Array":
                items_structure = items_node_nested.get("_")
                if items_structure and isinstance(items_structure, dict):
                    child_node = items_structure.get("_child")
                    if child_node and isinstance(child_node, dict) and child_node.get("type") == "Object":
                        child_fields = child_node.get("_")
                        if child_fields and isinstance(child_fields, dict):
                            print(f"  [解析器信息] API {api_id}: 使用 result._.items._._child._ 结构作为 row_content 的schema。")
                            return child_fields

            # Path 3: result._ itself is the schema (and not a wrapper with 'items')
            if not items_node_nested:
                is_not_wrapper = not ('total' in result_underscore_node and 'items' in result_underscore_node)
                is_schema_like = all(isinstance(v, dict) and "type" in v for v in result_underscore_node.values())
                if is_not_wrapper and is_schema_like and result_underscore_node:
                    print(f"  [解析器信息] API {api_id}: 使用 result._ 结构作为 row_content 的schema。")
                    return result_underscore_node

        # Path 4: result._ is a JSON string that needs parsing
        if result_underscore_node and isinstance(result_underscore_node, str):
            try:
                parsed_schema_from_string = json.loads(result_underscore_node)
                print(f"  [解析器信息] API {api_id}: 解析 result._ 字符串结构作为 row_content 的schema。")
                # This parsed schema might need further navigation if it's also a wrapper.
                # For simplicity, assuming it's the direct schema or needs to be handled by subsequent logic.
                return parsed_schema_from_string
            except json.JSONDecodeError:
                print(f"  [解析器错误] API {api_id}: result._ 字符串无法被解析为JSON。", file=sys.stderr)

        # Path 5: result itself is the schema
        if not items_node_direct and not result_underscore_node and \
           all(isinstance(v, dict) and "type" in v for v in result_node.values()) and result_node:
            print(f"  [解析器信息] API {api_id}: 使用 result 本身作为 row_content 的schema。")
            return result_node

        print(f"  [解析器警告] API ID {api_id} 未能从获取的schema中定位到 'row_content' 的详细字段定义。检查API文档结构。", file=sys.stderr)
        return None

    except requests.exceptions.RequestException as e:
        print(f"  [解析器错误] 请求API ID {api_id} 的schema时发生网络错误: {e}", file=sys.stderr)
        return None
    except (ValueError, json.JSONDecodeError) as e:
        print(f"  [解析器错误] 处理API ID {api_id} 的schema数据时发生错误: {e}", file=sys.stderr)
        return None

# --- Database and Core Logic ---
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
        print(f"    [信息] 表 {table_name} 无简单/JSON字段数据可插入。")
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
    parent_tid_value: int | None
):
    if isinstance(current_data, list):
        for item_data in current_data:
            if not isinstance(item_data, dict):
                print(f"  [警告] 列表中的项目不是字典，跳过: {str(item_data)[:100]} (目标表: {target_table_name})")
                continue
            populate_table_and_children_recursive(cursor, item_data, current_schema, target_table_name, fk_to_parent_column_name, parent_tid_value)
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
            print(f"  [警告] 字段 '{api_field_key}' 在提供的schema中未找到定义，跳过。 (目标表: {target_table_name})")
            continue

        field_type = field_schema.get("type")

        if field_type == "Object" and "_" in field_schema:
            if api_field_value is not None:
                child_table_base_name = get_detail_table_base_name_parser(to_snake_case_parser(target_table_name).replace(TABLE_PREFIX, "").replace("_detail",""), [api_field_key])
                child_table_full_name = get_full_table_name_parser(child_table_base_name)
                fk_in_child_col_name = f"{to_snake_case_parser(target_table_name)}_tid"
                children_to_process_later.append({
                    "data": api_field_value, "schema": field_schema["_"],
                    "table_name": child_table_full_name,
                    "fk_col": fk_in_child_col_name
                })
                # Rule for API 1001: specific Object fields are stored as JSON in parent
                if target_table_name == get_full_table_name_parser("base_info_detail"):
                    if db_col_name in ('liquidating_info', 'headquarters', 'brief_cancel'):
                         simple_fields_for_current_row[db_col_name] = json.dumps(api_field_value, ensure_ascii=False) if api_field_value else None
        elif field_type == "Array" and "_" in field_schema and "_child" in field_schema["_"] and \
             isinstance(field_schema["_"]["_child"], dict) and "_" in field_schema["_"]["_child"]:
            if api_field_value is not None and isinstance(api_field_value, list) and api_field_value:
                child_item_schema = field_schema["_"]["_child"]["_"]
                # Path for child table name uses current field key
                child_table_base_name = get_detail_table_base_name_parser(to_snake_case_parser(target_table_name).replace(TABLE_PREFIX, "").replace("_detail",""), [api_field_key])
                child_table_full_name = get_full_table_name_parser(child_table_base_name)
                fk_in_child_col_name = f"{to_snake_case_parser(target_table_name)}_tid"
                children_to_process_later.append({
                    "data": api_field_value, "schema": child_item_schema,
                    "table_name": child_table_full_name,
                    "fk_col": fk_in_child_col_name,
                    "is_list_of_items": True
                })
        else:
            if field_type == "Object" or field_type == "Array":
                simple_fields_for_current_row[db_col_name] = json.dumps(api_field_value, ensure_ascii=False) if api_field_value is not None else None
            else:
                simple_fields_for_current_row[db_col_name] = api_field_value

    current_row_tid = _insert_row(cursor, target_table_name, simple_fields_for_current_row)
    if current_row_tid is None and simple_fields_for_current_row:
        if simple_fields_for_current_row:
            raise Error(f"Insert into {target_table_name} failed to return a TID.")
        else:
            return

    for child_task in children_to_process_later:
        child_data = child_task["data"]
        child_schema = child_task["schema"]
        child_table_name = child_task["table_name"]
        fk_col_in_child = child_task["fk_col"]

        if child_task.get("is_list_of_items", False):
            for item_in_list in child_data:
                 populate_table_and_children_recursive(cursor, item_in_list, child_schema, child_table_name, fk_col_in_child, current_row_tid)
        else:
            populate_table_and_children_recursive(cursor, child_data, child_schema, child_table_name, fk_col_in_child, current_row_tid)

def parse_and_insert_row_content(cursor, master_item_tid: int, interface_id: int, raw_json_content: str, interface_dict: Dict):
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

    api_specific_row_content_schema = fetch_api_schema_from_source_parser(interface_id_str)
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
        parent_tid_value=master_item_tid
    )
    print(f"  - 完成主表TID: {master_item_tid} 的子表处理。")

def main():
    print("开始解析 ods_api_response_items 中的 raw_row_content 并填充子表 (增强版)...")
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
        if connection and connection.is_connected() and cursor: # Ensure cursor exists for rollback
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
    if DB_CONFIG.get('user') == 'your_username':
        print("[警告] 请在脚本顶部更新您的 `DB_CONFIG` (parser) 数据库连接信息！")
    else:
        main()
        print("\n--- 子表填充过程执行完毕 ---")
        print("请注意：此脚本实现了基于schema的递归子表填充。")
        print("确保 `fetch_api_schema_from_source_parser` 能准确获取或模拟各API的schema结构。")
```
