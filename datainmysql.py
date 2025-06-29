import json
import re
import requests
import mysql.connector
from mysql.connector import Error

# ============================= 1. 用戶配置區 =============================

# 請在此處配置您的數據庫連接信息
DB_CONFIG = {
    'host': 'localhost',  # 數據庫主機地址
    'user': 'your_username',  # 數據庫用戶名
    'password': 'your_password',  # 數據庫密碼
    'database': 'tianyancha_db'  # 您創建的數據庫名
}

# 請在此處填寫您從天眼查獲取的 API Token
TYC_API_TOKEN = 'YOUR_REAL_API_TOKEN'

# 您想要查詢的公司列表
COMPANIES_TO_PROCESS = [
    "小米科技有限责任公司",
    "华为技术有限公司"
]

# 從第一步複製過來的接口字典，用於構建請求和表名
INTERFACE_DICT = {
    "1001": ("base_info", "工商信息"),
    "880": ("certifications", "资质证书"),
    "998": ("equity_changes", "股权变更"),
    # ... 您可以根據需要添加或刪除其他接口
    # "946": ("suppliers", "供应商"),
    # "947": ("customers", "客户"),
}


# ============================= 2. 輔助函數和數據庫操作 =============================

def to_snake_case(name):
    """駝峰命名轉蛇形命名 (e.g., regStatus -> reg_status)"""
    name = re.sub(r'([a-z\d])([A-Z])', r'\1_\2', name)
    return name.replace("__", "_").lower()


def create_db_connection():
    """創建並返回一個數據庫連接"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            print("數據庫連接成功。")
            return connection
    except Error as e:
        print(f"數據庫連接失敗: {e}")
        return None


def fetch_api_data(company_name: str, api_path: str):
    """
    從天眼查的業務接口獲取指定公司的數據。
    注意：這裏的 URL 結構是基於天眼查通用 API 格式的推測，請根據您的實際 API 文檔進行調整。
    """
    # 業務數據接口的 URL 通常和元數據接口不同
    url = f"https://open.tianyancha.com/services/open/{api_path}/2.0"
    headers = {
        'Authorization': TYC_API_TOKEN
    }
    params = {
        'keyword': company_name
    }

    print(f"  正在從接口 '{api_path}' 獲取 '{company_name}' 的數據...")
    try:
        response = requests.get(url, headers=headers, params=params, timeout=20)
        response.raise_for_status()  # 如果請求失敗則拋出異常

        result = response.json()
        if result.get('error_code') == 0:
            print(f"  成功獲取數據。")
            return result.get('result')
        else:
            print(f"  API 返回錯誤: {result.get('reason')}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"  請求 API 時發生網絡錯誤: {e}")
        return None
    except json.JSONDecodeError:
        print(f"  無法解析 API 返回的 JSON 數據。")
        return None


def insert_data(cursor, table_name: str, data: dict):
    """
    將一個字典的數據插入到指定的數據庫表中。
    返回新插入行的 ID (lastrowid)。
    """
    # 將字典的鍵轉換為蛇形命名的列名
    columns = [to_snake_case(key) for key in data.keys()]
    # 創建對應的 %s 占位符
    placeholders = ['%s'] * len(columns)

    sql = f"INSERT INTO `{table_name}` ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"

    try:
        # 提取字典的值，並確保順序與列名一致
        values = list(data.values())
        cursor.execute(sql, values)
        # 返回新插入行的自增 ID，用於關聯子表
        return cursor.lastrowid
    except Error as e:
        print(f"\n[數據庫錯誤] 插入到表 `{table_name}` 失敗: {e}")
        print(f"  - SQL: {sql}")
        print(f"  - Data: {data}")
        raise  # 拋出異常，以便上層進行事務回滾


# ============================= 3. 核心處理邏輯 =============================

def process_and_insert(cursor, json_data, table_name_prefix: str, parent_id=None, parent_table_name=None):
    """
    遞歸地處理 JSON 數據，並將其插入到對應的數據庫表中。

    :param cursor: 數據庫游標
    :param json_data: 要處理的 JSON 對象或列表
    :param table_name_prefix: 表名的前綴 (如 'base_info', 'certifications')
    :param parent_id: 父記錄在數據庫中的 ID
    :param parent_table_name: 父表的全名 (如 'base_info')
    """
    if isinstance(json_data, list):
        # 如果是列表，遍歷其中每個元素並遞歸處理
        for item in json_data:
            process_and_insert(cursor, item, table_name_prefix, parent_id, parent_table_name)
        return

    if not isinstance(json_data, dict):
        # 如果不是字典或列表，则无法处理
        return

    # 1. 分離簡單字段和複雜字段 (列表/對象)
    simple_fields = {}
    complex_fields = {}

    for key, value in json_data.items():
        if isinstance(value, (dict, list)) and value:  # 僅處理非空的對象和列表
            complex_fields[key] = value
        elif not isinstance(value, (dict, list)):  # 處理簡單類型
            simple_fields[key] = value

    # 2. 插入當前層級的數據到主表
    current_table_name = to_snake_case(table_name_prefix)

    # 如果存在父ID，需要將外鍵添加到待插入數據中
    if parent_id and parent_table_name:
        foreign_key_column = f"{to_snake_case(parent_table_name)}_id"
        simple_fields[foreign_key_column] = parent_id

    # 只有在有簡單字段時才執行插入
    if not simple_fields:
        return

    # 執行插入並獲取新記錄的ID
    new_id = insert_data(cursor, current_table_name, simple_fields)
    print(f"    - 插入記錄到 `{current_table_name}` (ID: {new_id})")

    # 3. 遍歷複雜字段，遞歸調用自身以處理子表數據
    for key, value in complex_fields.items():
        # 構造子表的名稱，如 base_info_staff_list
        child_table_prefix = f"{table_name_prefix}_{key}"
        # 遞歸處理，傳入新創建的記錄ID作为父ID
        process_and_insert(cursor, value, child_table_prefix, new_id, current_table_name)


# ============================= 4. 主執行函數 =============================

def main():
    """主執行函數"""
    connection = create_db_connection()
    if not connection:
        return

    cursor = connection.cursor()

    try:
        for company in COMPANIES_TO_PROCESS:
            print(f"\n{'=' * 20} 開始處理公司: {company} {'=' * 20}")

            # 為每個公司遍歷需要查詢的接口
            for api_id, (table_prefix, chinese_name) in INTERFACE_DICT.items():

                # 從天眼查獲取數據
                api_data = fetch_api_data(company, table_prefix)

                if api_data:
                    # 開始遞歸插入過程
                    process_and_insert(cursor, api_data, table_prefix)

            # 處理完一個公司的所有接口後，提交事務
            print(f"完成公司 '{company}' 的所有數據處理，提交事務。")
            connection.commit()

    except Exception as e:
        print(f"\n處理過程中發生嚴重錯誤: {e}。事務將被回滾。")
        connection.rollback()
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("\n數據庫連接已關閉。")


if __name__ == '__main__':
    if TYC_API_TOKEN == 'YOUR_REAL_API_TOKEN' or DB_CONFIG['user'] == 'your_username':
        print("[警告] 請先在腳本中配置您的數據庫信息 (DB_CONFIG) 和天眼查 API Token (TYC_API_TOKEN)！")
    else:
        main()