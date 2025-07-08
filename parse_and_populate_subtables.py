import json
import mysql.connector
from mysql.connector import Error
import hashlib
import re
from typing import Dict, List, Any, Set

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

# This should be identical to the one in apijsontosql4.py
INTERFACE_DICT = {
    "1049": ("credit_ratings", "企业信用评级"),
    "884": ("tax_ratings", "税务评级"),
    "1001": ("base_info", "工商信息"),
    "1163": ("person_legal_proceedings", "法律诉讼(人员)"),
    "9999": ("a_very_long_interface_name_for_testing_abbreviation_rules", "超长接口名称测试缩写规则")
}

# TYPE_MAP might not be directly needed for data insertion if apijsontosql4 handles schema correctly,
# but it's good for reference or if we need to validate types based on schema.
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
    if len(core_name) <= max_core_len: return name # Should not happen if initial check passed
    name_hash = hashlib.md5(core_name.encode('utf-8')).hexdigest()[:5]
    hash_len = len(name_hash) + 1
    available_len_for_core = max_core_len - hash_len
    if available_len_for_core <= 0: # Highly unlikely
        return TABLE_PREFIX + core_name[:max_core_len - len(name_hash)] + name_hash
    truncated_core = core_name[:available_len_for_core]
    return f"{TABLE_PREFIX}{truncated_core}_{name_hash}"[:max_length]

def get_full_table_name_parser(base_name_without_prefix: str) -> str:
    prefixed_name = TABLE_PREFIX + base_name_without_prefix
    return shorten_table_name_parser(prefixed_name)

ACTUAL_MASTER_TABLE_NAME = get_full_table_name_parser(MASTER_TABLE_BASE_NAME)

def get_detail_table_base_name_parser(interface_table_prefix: str, path: List[str]) -> str:
    effective_path = [p for p in path if p != '_child'] # _child is a schema marker, not part of name path
    if not effective_path: # Top-level detail for an interface (e.g. from row_content directly)
         return to_snake_case_parser(f"{interface_table_prefix}_detail")
    return to_snake_case_parser(f"{interface_table_prefix}_{'_'.join(effective_path)}_detail")

# --- Schema Fetching (Crucial: Must align with apijsontosql4.py's live fetching) ---
def fetch_api_schema_from_source_parser(api_id: str) -> Dict | None:
    """
    Fetches the API schema structure.
    IMPORTANT: This function *must* replicate the exact logic of
    `fetch_api_schema_from_source` in `apijsontosql4.py` to ensure consistency.
    For brevity, the full replicated logic is not included here but is assumed.
    This placeholder will use a simplified mock for known APIs.
    """
    # This is where the full logic from apijsontosql4.py's fetch_api_schema_from_source would go.
    # It would make an HTTP request to get the live schema.
    # For this example, using simplified mock schemas based on previous discussions.

    print(f"  [解析器] 调用 fetch_api_schema_from_source_parser 为 API ID: {api_id}")
    # Mocked schemas based on previous discussions:
    if api_id == "1001": #工商信息 (schema for the content of 'result' or 'result._')
        # This schema should represent the fields directly inside the 'row_content' for API 1001
        # (e.g., 'cancelDate', 'regStatus', 'branchList', etc.)
        return {
            "id": {"type": "Number", "remark": "公司id"},
            "name": {"type": "String", "remark": "企业名"},
            "regStatus": {"type": "String", "remark": "企业状态"},
            "legalPersonName": {"type": "String", "remark": "法人"},
            "branchList": {"type": "Array", "remark":"分支机构","_": {"_child": {"type": "Object", "_": {
                "name": {"type": "String", "remark":"分支机构名称"}, "id": {"type": "Number"}, "regStatus":{"type":"String"}
            }}}},
            "shareHolderList": {"type": "Array", "remark":"股东信息","_": {"_child": {"type": "Object", "_": {
                "name": {"type": "String"}, "type": {"type": "Number"},
                "capital": {"type": "Array", "remark":"出资信息","_": {"_child": {"type":"Object", "_":{
                    "amomon":{"type":"String"}, "percent":{"type":"String"}
                }}}}
            }}}},
            "staffList": {"type": "Array", "remark":"主要人员","_": {"_child": {"type": "Object", "_": {"name": {"type": "String"}, "staffTypeName": {"type":"String"}}}}},
            "changeList": {"type": "Array", "remark":"变更记录","_": {"_child": {"type": "Object", "_": {"changeItem": {"type": "String"},"changeTime":{"type":"String"}}}}},
            "investList": {"type": "Array", "remark":"对外投资","_": {"_child": {"type": "Object", "_": {"name": {"type": "String"},"amount":{"type":"Number"}}}}},
            "reportList": {"type": "Array", "remark":"年报信息","_": {"_child": {"type": "Object", "_": {"reportYear": {"type": "String"},"totalSales":{"type":"String"}}}}},
            "licenseList": {"type": "Array", "remark":"行政许可","_": {"_child": {"type": "Object", "_": {"licencename": {"type": "String"},"todate":{"type":"String"}}}}},
            "liquidatingInfo": {"type": "Object", "remark":"清算信息","_": {"status": {"type": "String"}}}, # Stored as JSON
            "headquarters": {"type": "Object", "remark":"总公司信息","_": {"name": {"type": "String"}}}, # Stored as JSON
            "briefCancel": {"type": "Object", "remark":"简易注销信息","_": {"status": {"type": "String"}}}, # Stored as JSON
             # ... add all other simple fields from ods_base_info_detail ...
            "legalPersonType": {"type": "Number"}, "regNumber": {"type": "String"}, "industry": {"type": "String"},
            "companyOrgType": {"type": "String"}, "regLocation": {"type": "String"}, "estiblishTime": {"type": "String"},
            "fromTime": {"type": "String"}, "toTime": {"type": "String"}, "businessScope": {"type": "String"},
            "approvedTime": {"type": "String"}, "regCapital": {"type": "String"}, "regInstitute": {"type": "String"},
            "orgNumber": {"type": "String"}, "creditCode": {"type": "String"}, "property3": {"type": "String"},
            "updatetime": {"type": "String"}, "companyId": {"type": "Number"}, "taxNumber": {"type": "String"},
            "email": {"type": "String"}, "website": {"type": "String"}, "phoneNumber": {"type": "String"},
            "revokeDate": {"type": "String"}, "revokeReason": {"type": "String"}, "cancelReason": {"type": "String"}
        }
    elif api_id == "1049": #企业信用评级 (schema for items in result._.items array)
         return {
            "ratingOutlook": {"type": "String"}, "ratingDate": {"type": "String"}, "gid": {"type": "Number"},
            "ratingCompanyName": {"type": "String"}, "bondCreditLevel": {"type": "String"},
            "logo": {"type": "String"}, "alias": {"type": "String"}, "subjectLevel": {"type": "String"}
        }
    print(f"  [解析器警告] 未找到API ID {api_id} 的mock schema。请确保fetch_api_schema_from_source_parser已正确实现。")
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
    """Helper to insert a single row and return the new tid."""
    if not data_dict: # No data to insert (e.g. all fields were complex and handled by recursion)
        print(f"    [信息] 表 {table_name} 无简单/JSON字段数据可插入。")
        return None # Or raise error if this state is unexpected for a given table

    columns = list(data_dict.keys())
    placeholders = ['%s'] * len(columns)
    sql = f"INSERT INTO `{table_name}` ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
    try:
        cursor.execute(sql, list(data_dict.values()))
        # print(f"    - 成功插入数据到 {table_name} (TID: {cursor.lastrowid})")
        return cursor.lastrowid
    except Error as e:
        print(f"    - [数据库错误] 插入到表 `{table_name}` 失败: {e}")
        print(f"      - SQL: {sql}")
        print(f"      - Data: {str(data_dict)[:500]}...")
        raise # Re-raise to be caught by transaction handler in main

def populate_table_and_children_recursive(
    cursor,
    current_data: Any, # Can be a dict (for an object) or a list of dicts (for array items)
    current_schema: Dict[str, Any],
    target_table_name: str, # Full name of the table to insert current_data into
    fk_to_parent_column_name: str | None, # Name of FK column in target_table_name that points to parent
    parent_tid_value: int | None # Value of parent_tid for the FK
):
    """
    Recursively populates a table and its children based on data and schema.
    """
    if isinstance(current_data, list): # If current_data is a list of items for the target_table_name
        for item_data in current_data:
            if not isinstance(item_data, dict):
                print(f"  [警告] 列表中的项目不是字典，跳过: {item_data} (目标表: {target_table_name})")
                continue
            # Each item in the list gets its own row and potentially its own children
            populate_table_and_children_recursive(cursor, item_data, current_schema, target_table_name, fk_to_parent_column_name, parent_tid_value)
        return

    # If current_data is a dictionary (a single object/row)
    if not isinstance(current_data, dict):
        print(f"  [警告] 当前数据不是字典，无法处理: {current_data} (目标表: {target_table_name})")
        return

    simple_fields_for_current_row = {}
    if fk_to_parent_column_name and parent_tid_value is not None:
        simple_fields_for_current_row[fk_to_parent_column_name] = parent_tid_value

    children_to_process_later = [] # Store (child_data, child_schema, child_table_name, new_fk_col_name_for_child)

    for api_field_key, api_field_value in current_data.items():
        db_col_name = to_snake_case_parser(api_field_key)
        field_schema = current_schema.get(api_field_key)

        if not field_schema:
            print(f"  [警告] 字段 '{api_field_key}' 在提供的schema中未找到定义，跳过。 (目标表: {target_table_name})")
            continue

        field_type = field_schema.get("type")

        if field_type == "Object" and "_" in field_schema: # Nested Object
            if api_field_value is not None: # Only process if data exists
                # This object becomes a new child table or is stored as JSON
                # Policy: if schema has "_", it's a structured object for a child table.
                # If apijsontosql4.py created a JSON column for this in *this* target_table_name,
                # then this logic needs to know that.
                # For now, assume if it has "_", it's a child table.
                child_table_base_name = get_detail_table_base_name_parser(to_snake_case_parser(target_table_name).replace(TABLE_PREFIX, "").replace("_detail",""), [api_field_key]) # Path is just the field key
                child_table_full_name = get_full_table_name_parser(child_table_base_name)

                # The FK in child table will point to current target_table_name's tid
                fk_in_child_col_name = f"{to_snake_case_parser(target_table_name)}_tid"

                children_to_process_later.append({
                    "data": api_field_value, "schema": field_schema["_"],
                    "table_name": child_table_full_name,
                    "fk_col": fk_in_child_col_name
                })
                # If apijsontosql4 also creates a JSON column in parent for this object (current policy)
                # we should also populate that if this script is to be complete.
                # For now, focusing on child table population.
                # If 'liquidatingInfo' is an example, it is Object but stored as JSON in parent.
                # This needs a clear rule: when is an Object a JSON column vs a child table?
                # Rule from apijsontosql4: if it's a nested object, it creates a JSON column *and* recurses.
                # So, we might need to insert JSON here too.
                if target_table_name == get_full_table_name_parser("base_info_detail"): # Example for API 1001
                    if db_col_name in ('liquidating_info', 'headquarters', 'brief_cancel'): # Known JSON fields
                         simple_fields_for_current_row[db_col_name] = json.dumps(api_field_value, ensure_ascii=False) if api_field_value else None


        elif field_type == "Array" and "_" in field_schema and "_child" in field_schema["_"] and \
             isinstance(field_schema["_"]["_child"], dict) and "_" in field_schema["_"]["_child"]: # Array of Objects
            if api_field_value is not None and isinstance(api_field_value, list) and api_field_value: # Ensure it's a non-empty list
                child_item_schema = field_schema["_"]["_child"]["_"]
                child_table_base_name = get_detail_table_base_name_parser(to_snake_case_parser(target_table_name).replace(TABLE_PREFIX, "").replace("_detail",""), [api_field_key])
                child_table_full_name = get_full_table_name_parser(child_table_base_name)
                fk_in_child_col_name = f"{to_snake_case_parser(target_table_name)}_tid"

                children_to_process_later.append({
                    "data": api_field_value, "schema": child_item_schema, # Schema is for *each item* in array
                    "table_name": child_table_full_name,
                    "fk_col": fk_in_child_col_name,
                    "is_list_of_items": True # Flag to iterate list in recursive call
                })
        else: # Simple type or Object/Array to be stored as-is (e.g. if schema type is just "Object" not "Object with _")
            if field_type == "Object" or field_type == "Array": # Store as JSON string if schema says Object/Array but no further structure
                simple_fields_for_current_row[db_col_name] = json.dumps(api_field_value, ensure_ascii=False) if api_field_value is not None else None
            else: # String, Number, Boolean, Date
                simple_fields_for_current_row[db_col_name] = api_field_value

    # Insert current row's simple/JSON fields
    current_row_tid = _insert_row(cursor, target_table_name, simple_fields_for_current_row)
    if current_row_tid is None and simple_fields_for_current_row : # If fields existed but insert failed or returned no ID
        print(f"  [错误] 未能为表 {target_table_name} 获取TID，无法处理其子表。数据: {simple_fields_for_current_row}")
        # Depending on policy, this could raise an error to rollback the transaction for parent item.
        # For now, if simple_fields_for_current_row was empty, it's fine (no row inserted, no children).
        # If it was not empty but current_row_tid is None, it's an error from _insert_row.
        if simple_fields_for_current_row: # If there was actual data to insert for current row.
            raise Error(f"Insert into {target_table_name} failed to return a TID.")
        else: # No actual data for current row (e.g. an object that only contained other lists/objects)
            return # No row inserted for current_data, so no children can be linked.


    # Process children, passing the new current_row_tid as their parent_tid_value
    for child_task in children_to_process_later:
        child_data = child_task["data"]
        child_schema = child_task["schema"]
        child_table_name = child_task["table_name"]
        fk_col_in_child = child_task["fk_col"]

        if child_task.get("is_list_of_items", False): # If it's an array of items for the child table
            for item_in_list in child_data:
                 populate_table_and_children_recursive(cursor, item_in_list, child_schema, child_table_name, fk_col_in_child, current_row_tid)
        else: # If it's a single object for the child table
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
    # Check if parsed_json is the wrapped structure (e.g., from a direct Tianyancha API call stored in raw_row_content)
    # This heuristic assumes 'result' and 'reason' (or 'error_code') indicate a wrapped response.
    # AND that the 'row_content' stored by dataetlinsert.py was NOT this wrapped structure,
    # but rather the content of such a 'result' node if the source API was wrapped.
    # The user clarification implies raw_row_content *might* be wrapped.

    if isinstance(parsed_json, dict) and 'result' in parsed_json and ('reason' in parsed_json or 'error_code' in parsed_json):
        is_successful_wrapper = parsed_json.get('reason') == 'ok' or parsed_json.get('error_code') == 0
        if is_successful_wrapper:
            actual_business_data = parsed_json.get('result')
            if actual_business_data is None: # Handles 'result': null
                print(f"  - [信息] raw_json 是带包装结构且成功，但 'result' 内容为null。TID: {master_item_tid}。无业务数据可处理。")
                return # No data to process
            print(f"  - 检测到外层包装JSON，提取 'result' 节点内容进行处理。TID: {master_item_tid}")
        else:
            error_info = parsed_json.get('reason', f"error_code: {parsed_json.get('error_code')}")
            print(f"  - [警告] raw_json 是带包装结构但表示失败/错误: '{error_info}'. TID: {master_item_tid}。跳过处理。")
            # TODO: Potentially update master table status to 'ERROR_IN_RAW_DATA'
            return
    elif isinstance(parsed_json, (dict, list)): # Assumed to be direct business data (already unwrapped or never wrapped)
        actual_business_data = parsed_json
        print(f"  - raw_json 被解析为直接的业务数据（字典或列表）。TID: {master_item_tid}")
    else:
        print(f"  - [错误] 解析后的raw_json既不是预期的包装结构也不是字典/列表。类型: {type(parsed_json)}，TID: {master_item_tid}。跳过处理。")
        return

    # After potentially unwrapping, check if actual_business_data is something workable
    if actual_business_data is None: # Could happen if 'result' was present but null, and it wasn't direct data
        print(f"  - [信息] 最终业务数据为None，TID: {master_item_tid}。无业务数据可处理。")
        return
    if isinstance(actual_business_data, list) and not actual_business_data: # Empty list is valid for "no items"
        print(f"  - [信息] 最终业务数据为空列表，TID: {master_item_tid}。populate_table_and_children_recursive 将处理此情况。")
        # Let populate_table_and_children_recursive handle empty list (it should do nothing)
    elif not isinstance(actual_business_data, (dict, list)): # Must be dict or list to proceed
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

    cursor = None # Initialize cursor to None
    current_processing_tid = None # For logging in case of error
    try:
        cursor = connection.cursor(dictionary=True)
        query = f"SELECT tid, interface_id, raw_row_content FROM `{ACTUAL_MASTER_TABLE_NAME}` WHERE raw_row_content IS NOT NULL AND is_row_content_processed = FALSE"
        # For testing, you might want to limit: query += " LIMIT 1"
        # Or process a specific problematic tid: query = f"SELECT ... WHERE tid = YOUR_TID_HERE"

        cursor.execute(query)
        items_to_process = cursor.fetchall()
        print(f"找到 {len(items_to_process)} 条待处理记录。")

        for item in items_to_process:
            current_processing_tid = item['tid'] # For error logging
            master_tid = item['tid']
            interface_id = item['interface_id']
            raw_json = item['raw_row_content']

            print(f"--- 开始处理主记录 TID: {master_tid} ---")
            # Start a transaction for this master record's children
            # connection.start_transaction() # Not all connectors might have this; use set autocommit=0 / commit/rollback
            cursor.execute("START TRANSACTION;") # Explicit transaction start
            print(f"  - 事务开始 for TID: {master_tid}")


            parse_and_insert_row_content(cursor, master_tid, interface_id, raw_json, INTERFACE_DICT)

            update_sql = f"UPDATE `{ACTUAL_MASTER_TABLE_NAME}` SET is_row_content_processed = TRUE WHERE tid = %s"
            cursor.execute(update_sql, (master_tid,))
            print(f"  - 标记主记录 TID {master_tid} 为已处理。")

            # connection.commit()
            cursor.execute("COMMIT;")
            print(f"  - 事务提交 for TID: {master_tid}")
            print(f"--- 完成处理主记录 TID: {master_tid} ---")


    except Error as e:
        print(f"处理主表数据时发生数据库错误 (当前处理TID: {current_processing_tid if current_processing_tid else 'N/A'}): {e}")
        if connection and connection.is_connected():
            print("  - 正在回滚当前事务...")
            # connection.rollback()
            cursor.execute("ROLLBACK;")
            print("  - 事务已回滚。")
    except Exception as ex: # Catch other Python errors
        print(f"处理过程中发生非数据库错误 (当前处理TID: {current_processing_tid if current_processing_tid else 'N/A'}): {ex}")
        import traceback
        traceback.print_exc()
        if connection and connection.is_connected() and cursor: # Check cursor too
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
