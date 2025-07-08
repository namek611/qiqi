import json
import re
import requests
import mysql.connector
from mysql.connector import Error
from typing import List, Dict, Any
import hashlib # For table name shortening if needed by apijsontosql4.py's logic

# ============================= 0. 全局常量与辅助函数导入 =============================
# 从 apijsontosql4.py 复制或导入相同的表名生成逻辑
MYSQL_MAX_TABLE_NAME_LENGTH = 64
TABLE_PREFIX = "ods_"

def to_snake_case_data_insert(name: str) -> str: # Renamed to avoid conflict if imported
    name = re.sub(r'([a-z\d])([A-Z])', r'\1_\2', name)
    return name.replace("__", "_").lower()

def shorten_table_name_data_insert(name: str, max_length: int = MYSQL_MAX_TABLE_NAME_LENGTH) -> str:
    if len(name) <= max_length:
        return name
    prefix_len = len(TABLE_PREFIX)
    core_name = name[prefix_len:]
    max_core_len = max_length - prefix_len
    if len(core_name) <= max_core_len:
        return name
    name_hash = hashlib.md5(core_name.encode('utf-8')).hexdigest()[:5]
    hash_len = len(name_hash) + 1
    available_len_for_core = max_core_len - hash_len
    if available_len_for_core <= 0:
        return TABLE_PREFIX + core_name[:max_core_len - (len(name_hash))] + name_hash
    parts = core_name.split('_')
    if len(parts) > 2:
        truncated_core = core_name[:available_len_for_core]
        shortened_name = f"{TABLE_PREFIX}{truncated_core}_{name_hash}"
    else:
        truncated_core = core_name[:available_len_for_core]
        shortened_name = f"{TABLE_PREFIX}{truncated_core}_{name_hash}"
    return shortened_name[:max_length]

def get_full_table_name_data_insert(base_name_without_prefix: str) -> str:
    prefixed_name = TABLE_PREFIX + base_name_without_prefix
    return shorten_table_name_data_insert(prefixed_name)

# 主表的基础名 (不含ods_前缀)
MASTER_TABLE_BASE_NAME = "api_response_items"
# 获取主表的实际完整名称（带ods_前缀和可能的缩写）
ACTUAL_MASTER_TABLE_NAME = get_full_table_name_data_insert(MASTER_TABLE_BASE_NAME)


# ============================= 1. 用户配置区 =============================
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Ec2024_12',
    'database': 'rsk_mail' # 例如: 'rsk_data_v5_ods'
}

COMPANIES_TO_PROCESS = [
    "上海建工集团股份有限公司"
]

# 接口字典更新：
# (interface_table_prefix_for_detail, chinese_name)
# interface_table_prefix_for_detail 是用于生成详情表名的基础部分 (不含ods_, 不含_detail后缀)
# 例如 "credit_ratings" 会生成详情表 ods_credit_ratings_detail (或缩写版)
INTERFACE_DICT = {
    "1049": ("credit_ratings", "企业信用评级"),
    "884": ("tax_ratings", "税务评级"),
    "1163": ("person_legal_proceedings", "法律诉讼(人员)"),
    "9999": ("a_very_long_interface_name_for_testing_abbreviation_rules", "超长接口名称测试缩写规则")
}

# ============================= 2. 辅助函数和数据库操作 =============================

def create_db_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            print("数据库连接成功。")
            return connection
    except Error as e:
        print(f"数据库连接失败: {e}")
        return None

def fetch_api_data(company_name: str, api_id: str) -> List[Dict[str, Any]] | None:
    url = f"http://10.50.74.8:38081/fireeyes/interface"
    headers = {'Content-Type': 'application/json', 'x-scg-requestid': '', 'x-scg-servicename': 'S_XXX_XXX_XXXX', 'x-scg-caller': 'DMS'}
    params = {"name": company_name, "user_code": "DMS", "interface_id": str(api_id), "is_need_update_period": False}
    print(f"  正在从接口 ID '{api_id}' 获取 '{company_name}' 的数据...")
    try:
        response = requests.post(url, data=json.dumps(params), headers=headers, timeout=20)
        response.raise_for_status()
        result = response.json()
        if result.get('err_code') == 0:
            items = result.get('items')
            if items is not None:
                 print(f"  成功获取 {len(items)} 条数据。")
                 return items
            else:
                print(f"  成功获取数据，但 'items' 字段为空或不存在。")
                return []
        else:
            print(f"  API 返回错误 (err_code: {result.get('err_code')}): {result.get('reason', '无具体错误信息')}")
            return None
    except requests.exceptions.Timeout:
        print(f"  请求 API ID '{api_id}' 超时。")
        return None
    except requests.exceptions.RequestException as e:
        print(f"  请求 API ID '{api_id}' 时发生网络错误: {e}")
        return None
    except json.JSONDecodeError:
        print(f"  无法解析 API ID '{api_id}' 返回的 JSON 数据。原始响应: {response.text[:500]}...")
        return None

def insert_master_data(cursor, item_data: Dict[str, Any]) -> int | None:
    """
    将主数据插入到实际的主表 (如 `ods_api_response_items`)。
    返回新插入行的 TID。
    """
    master_data = {
        'company_name': item_data.get('name'),
        'disabled': item_data.get('disabled'),
        'last_update_time': item_data.get('last_update_time'),
        'interface_id': item_data.get('interface_id'),
        'interface_name': item_data.get('interface_name'),
    }

    # Add raw_row_content, serialized to JSON
    raw_content = item_data.get('row_content')
    if raw_content is not None and isinstance(raw_content, dict):
        try:
            master_data['raw_row_content'] = json.dumps(raw_content, ensure_ascii=False)
        except TypeError as e:
            print(f"  [警告] 序列化 row_content 到JSON失败: {e}。将存为NULL。row_content: {str(raw_content)[:200]}...")
            master_data['raw_row_content'] = None
    elif raw_content is not None: # Not a dict, store as is if simple, or null if complex non-dict
        if isinstance(raw_content, (str, int, float, bool)):
             master_data['raw_row_content'] = raw_content # Or json.dumps(raw_content) to be safe if column is JSON
        else:
            print(f"  [警告] row_content 不是字典类型也不是简单类型，将存为NULL。类型: {type(raw_content)}")
            master_data['raw_row_content'] = None
    else:
        master_data['raw_row_content'] = None

    master_data_cleaned = {k: v for k, v in master_data.items() if v is not None}
    columns = [to_snake_case_data_insert(k) for k in master_data_cleaned.keys()] # Ensure snake case for columns
    placeholders = ['%s'] * len(columns)

    # 使用 ACTUAL_MASTER_TABLE_NAME
    sql = f"INSERT INTO `{ACTUAL_MASTER_TABLE_NAME}` ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"

    try:
        values = list(master_data_cleaned.values())
        cursor.execute(sql, values)
        return cursor.lastrowid # lastrowid 返回的是自增主键的值，这里是 tid
    except Error as e:
        print(f"\n[数据库错误] 插入到主表 `{ACTUAL_MASTER_TABLE_NAME}` 失败: {e}")
        print(f"  - SQL: {sql}")
        print(f"  - Data: {master_data_cleaned}")
        raise

def insert_detail_data(cursor, detail_table_name: str, detail_data: Dict[str, Any], master_item_tid: int, master_table_actual_name: str):
    """
    将行项目内容 (row_content) 插入到对应的详情表。
    外键列名现在是 `ods_api_response_items_tid` (或主表缩写名_tid)。
    """
    if not isinstance(detail_data, dict):
        print(f"  [警告] 详情数据不是字典格式，无法插入到 {detail_table_name}。数据: {detail_data}")
        return

    # 外键列名是主表名（蛇形）+ _tid
    foreign_key_column_name = f"{to_snake_case_data_insert(master_table_actual_name)}_tid"
    data_to_insert = {}

    # Predefined set of fields (snake_case) known to be JSON in specific tables.
    # This might need to be more dynamic or per-API if structures vary widely.
    # For API 1001 (base_info), these are the JSON fields in ods_base_info_detail
    # Note: These should be the *snake_case* versions of the API's field names.
    # API field names: 'liquidatingInfo', 'briefCancel', 'headquarters'
    known_json_fields = {
        'liquidating_info',
        'brief_cancel',
        'headquarters'
    }

    for key, value in detail_data.items():
        col_name_snake = to_snake_case_data_insert(key)

        if isinstance(value, list):
            # Skip list types, should be handled by child tables (future enhancement)
            print(f"  [信息] 字段 '{key}' (列: {col_name_snake}) 是列表类型，跳过直接插入到 {detail_table_name}。应由子表处理。")
            continue
        elif isinstance(value, dict):
            if col_name_snake in known_json_fields:
                try:
                    data_to_insert[col_name_snake] = json.dumps(value, ensure_ascii=False)
                except TypeError as e:
                    print(f"  [警告] 字段 '{key}' (列: {col_name_snake}) 序列化为JSON失败: {e}。值: {str(value)[:100]}... 跳过。")
            else:
                # Skip dict types if not explicitly defined as JSON columns, might be for child tables
                print(f"  [信息] 字段 '{key}' (列: {col_name_snake}) 是字典类型，但未在预定义JSON字段中，跳过直接插入到 {detail_table_name}。可能应由子表处理。")
            continue

        # For other simple types (str, int, float, bool, None)
        data_to_insert[col_name_snake] = value

    data_to_insert[foreign_key_column_name] = master_item_tid

    # It's generally safer to let the DB handle None for nullable columns,
    # and error out if a NOT NULL column receives None.
    # So, we don't filter out None values here.
    data_to_insert_cleaned = data_to_insert # Keep Nones, DB will validate.

    if not data_to_insert_cleaned : # Check if anything is left to insert besides FK
        # If only FK is present, it means all other fields were filtered.
        # This check might be too simplistic if a table *only* has an FK and other fields are optional.
        # However, if detail_data was originally empty, this is valid.
        if not any(k for k in detail_data.keys()): # Original detail_data was empty
             print(f"  [信息] row_content 为空，不向详情表 `{detail_table_name}` 插入数据。")
             return
        # If detail_data was not empty, but all fields got filtered, it's a bit ambiguous.
        # For now, proceed if at least the FK is there.

    if foreign_key_column_name not in data_to_insert_cleaned:
         print(f"  [警告] 外键 '{foreign_key_column_name}' 未能添加到待插入数据中，无法插入到 {detail_table_name}。数据: {data_to_insert_cleaned}")
         return


    columns = list(data_to_insert_cleaned.keys())
    # Ensure there are columns to insert beyond just a potential FK if all fields were complex types
    if not columns or (len(columns) == 1 and foreign_key_column_name in columns and not any(k for k in detail_data.keys())) :
        if not any(k for k in detail_data.keys()): # Original detail_data was empty
             print(f"  [信息] row_content 为空或所有字段被过滤，且无简单字段可插入到详情表 `{detail_table_name}`。")
             return
        # If detail_data had content but all were filtered, we might still insert if only FK is needed by schema.
        # However, most detail tables would have other data.
        # Let's assume if only FK is left, and original data wasn't empty, something is amiss or table is just a link.
        # For safety, if no actual data columns from row_content made it, we can skip.
        value_columns = [col for col in columns if col != foreign_key_column_name]
        if not value_columns and any(k for k in detail_data.keys()): # Original data existed, but all were filtered
            print(f"  [信息] row_content 中所有字段均为复杂类型或不适用于直接插入，详情表 `{detail_table_name}` 本次无数据列更新。")
            # Depending on requirements, one might still insert if the table allows all other columns to be NULL.
            # For now, if no data columns, we will not proceed with the insert to avoid empty rows beyond FK.
            return


    placeholders = ['%s'] * len(columns)
    sql = f"INSERT INTO `{detail_table_name}` ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"

    try:
        values = list(data_to_insert_cleaned.values())
        cursor.execute(sql, values)
    except Error as e:
        print(f"\n[数据库错误] 插入到详情表 `{detail_table_name}` 失败: {e}")
        print(f"  - SQL: {sql}")
        print(f"  - Data: {data_to_insert_cleaned}")
        if e.errno == 1054:
            print(f"  [提示] 请检查表 `{detail_table_name}` 是否包含以下所有列 (蛇形命名): {list(data_to_insert_cleaned.keys())}")
            print(f"          或者 `apijsontosql4.py` 生成的表结构是否与实际数据字段匹配 (特别是外键名 `{foreign_key_column_name}` 是否存在于表中)。")
        raise

# ============================= 3. 核心处理逻辑 =============================

def process_and_insert_api_items(
    cursor,
    api_items: List[Dict[str, Any]],
    interface_id_str: str,
    master_table_actual_name: str # 传入主表的实际名称
):
    if interface_id_str not in INTERFACE_DICT:
        print(f"  [警告] 接口ID '{interface_id_str}' 未在 INTERFACE_DICT中配置，跳过处理。")
        return

    interface_table_prefix_for_detail, _ = INTERFACE_DICT[interface_id_str]
    # 构建详情表的基础名 (不含ods_, 不含路径, 但含_detail)
    detail_table_base_name = f"{interface_table_prefix_for_detail}_detail"
    # 获取详情表的完整实际名称 (带ods_前缀和可能的缩写)
    actual_detail_table_name = get_full_table_name_data_insert(detail_table_base_name)

    for item in api_items:
        master_tid = insert_master_data(cursor, item) # 返回的是主表的 tid
        if master_tid is None:
            print(f"  [错误] 插入主数据（包括raw_row_content）失败，跳过此条目: {item.get('name')}")
            continue

        print(f"    - 主数据（含raw_row_content）插入到 `{master_table_actual_name}` (TID: {master_tid}) for company '{item.get('name')}'")

        # row_content = item.get('row_content') # 保留此行以备调试或未来可能的双重写入策略
        # Per Option A, insert_detail_data call is removed.
        # Sub-table population will be handled by a new script using raw_row_content from the master table.
        # if row_content and isinstance(row_content, dict):
            # insert_detail_data(cursor, actual_detail_table_name, row_content, master_tid, master_table_actual_name)
            # print(f"      - [旧逻辑已注释] 详情数据插入到 `{actual_detail_table_name}` (master_tid: {master_tid})")
        # elif row_content:
            # print(f"      - [旧逻辑已注释] `row_content` 不是预期的字典格式，无法处理。内容: {type(row_content)}")
        # else:
            # print(f"      - [旧逻辑已注释] 此条目无 `row_content` 数据。")

# ============================= 4. 主执行函数 =============================

def main():
    connection = create_db_connection()
    if not connection:
        print("无法连接到数据库，程序退出。")
        return

    cursor = connection.cursor()
    # 获取主表的实际名称，因为外键列名和引用都需要它
    master_table_actual_name = get_full_table_name_data_insert(MASTER_TABLE_BASE_NAME)

    try:
        for company_name in COMPANIES_TO_PROCESS:
            print(f"\n{'=' * 20} 开始处理公司: {company_name} {'=' * 20}")

            for api_id_str, config_tuple in INTERFACE_DICT.items():
                chinese_name = config_tuple[1]
                print(f"\n  处理接口: {chinese_name} (ID: {api_id_str})")
                api_items_data = fetch_api_data(company_name, api_id_str)

                if api_items_data is not None:
                    if api_items_data:
                        process_and_insert_api_items(cursor, api_items_data, api_id_str, master_table_actual_name)
                    else:
                        print(f"    接口 {chinese_name} (ID: {api_id_str}) 对公司 '{company_name}' 返回了空列表，无需插入数据。")
                else:
                    print(f"    未能获取接口 {chinese_name} (ID: {api_id_str}) 的数据，跳过。")

            print(f"\n完成公司 '{company_name}' 的所有数据处理，准备提交事务。")
            connection.commit()
            print(f"事务已提交。")

    except Exception as e:
        print(f"\n处理过程中发生未捕获的严重错误: {e}。事务将被回滚。")
        if connection.is_connected():
            connection.rollback()
            print("事务已回滚。")
    finally:
        if connection and connection.is_connected():
            if cursor:
                cursor.close()
            connection.close()
            print("\n数据库连接已关闭。")

if __name__ == '__main__':
    if DB_CONFIG.get('user') == 'your_username' or DB_CONFIG.get('database') == 'rsk_mail_v3_example': # Generic example db name
        print("-" * 60)
        print("[警告] 请务必在脚本顶部更新您的 `DB_CONFIG` 数据库连接信息！")
        print(f"        当前用户: {DB_CONFIG.get('user')}, 数据库: {DB_CONFIG.get('database')}")
        print("-" * 60)
    else:
        main()
        print("\n--- 数据ETL过程执行完毕 ---")
        print(f"请检查数据库中的 `{ACTUAL_MASTER_TABLE_NAME}` 表以及相关的详情表。")
        print("同时留意控制台输出中是否有错误或警告信息。")
