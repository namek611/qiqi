import json
import re
import requests
import mysql.connector
from mysql.connector import Error

# ============================= 1. 用户配置区 =============================

# 请在此处配置您的数据库连接信息
DB_CONFIG = {
    'host': 'localhost',  # 数据库主机地址
    'user': 'root',  # 数据库用户名
    'password': 'Ec2024_12',  # 数据库密码
    'database': 'rsk_mail'  # 您创建的数据库名
}


# 您想要查询的公司列表
COMPANIES_TO_PROCESS = [
    "上海建工集团股份有限公司"
]

# 从第一步复制过来的接口字典，用于构建请求和表名
INTERFACE_DICT = {
    "1049": ("credit_ratings", "企业信用评级"),
    # "884": ("tax_ratings", "税务评级"),
    "1163": ("person_legal_proceedings", "法律诉讼(人员)"),
    "1036": ("bankruptcy_cases", "破产重整"),
    "843": ("dishonest_persons", "失信人"),
}


# ============================= 2. 辅助函数和数据库操作 =============================

def to_snake_case(name):
    """驼峰命名转蛇形命名 (e.g., regStatus -> reg_status)"""
    name = re.sub(r'([a-z\d])([A-Z])', r'\1_\2', name)
    return name.replace("__", "_").lower()


def create_db_connection():
    """创建并返回一个数据库连接"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            print("数据库连接成功。")
            return connection
    except Error as e:
        print(f"数据库连接失败: {e}")
        return None


def fetch_api_data(company_name: str, api_path: str,api_id: str):
    """
    从变更过的业务接口获取指定公司的数据。

    """
   
    url = f"http://10.50.74.8:38081/fireeyes/interface"
    content_type = 'application/json'
    x_scg_requestid = ''
    x_scg_servicename = 'S_XXX_XXX_XXXX'
    x_scg_caller = 'DMS'
    x_scg_sign = ''
    headers = {'Content-Type': content_type, 'x-scg-requestid': x_scg_requestid, 'x-scg-servicename': x_scg_servicename,
               'x-scg-caller': x_scg_caller}
    params = {
        "name": company_name,
        "user_code": "DMS",
        "interface_id": api_id,
        "is_need_update_period": False
    }

    print(f"  正在从接口 '{api_path}' 获取 '{company_name}' 的数据...")
    try:
        response = requests.post(url, data=json.dumps(params), headers=headers)
#         response="""{"err_code":0,"items":[{"name":"上海建工集团股份有限公司","row_content":{"ratingOutlook":"稳定","ratingDate":"2021-09-17","gid":24703069,"ratingCompanyName":"中债资信评估有限责任公司","bondCreditLevel":"","logo":"https://img5.tianyancha.com/logo/lll/6f0c46e529b0a2db4737c1e009d32ff4.png@!f_200x200","alias":"中债资信","subjectLevel":"AA+ pi"},"disabled":false,"last_update_time":"2025-07-04T07:45:29.950765","interface_id":1049,"interface_name":"企业信用评级"},{"name":"上海建工集团股份有限公司","row_content":{"ratingOutlook":"","ratingDate":"2015-10-26","gid":24498476,"ratingCompanyName":"中诚信国际信用评级有限责任公司","bondCreditLevel":"AAA","logo":"https://img5.tianyancha.com/logo/lll/7706e105be85a0fb10c8000ac3152e90.png@!f_200x200","alias":"中诚信","subjectLevel":""},"disabled":false,"last_update_time":"2025-07-04T07:45:29.950765","interface_id":1049,"interface_name":"企业信用评级"}]}
# """
        # response.raise_for_status()  # 如果请求失败则抛出异常
        # print(response.text)

        result = response.json()
        print(result)
        # print(result.get('err_code'))
        if result.get('err_code') == 0:
            print(f"  成功获取数据。")
            print(result.get('items'))
            return result.get('items')
        else:
            print(f"  API 返回错误: {result.get('reason')}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"  请求 API 时发生网络错误: {e}")
        return None
    except json.JSONDecodeError:
        print(f"  无法解析 API 返回的 JSON 数据。")
        return None


def insert_data(cursor, table_name: str, data: dict):
    """
    将一个字典的数据插入到指定的数据库表中。
    返回新插入行的 ID (lastrowid)。
    """
    # 将字典的键转换为蛇形命名的列名
    columns = [to_snake_case(key) for key in data.keys()]
    # 创建对应的 %s 占位符
    placeholders = ['%s'] * len(columns)

    sql = f"INSERT INTO `{table_name}` ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"

    try:
        # 提取字典的值，并确保顺序与列名一致
        values = list(data.values())
        cursor.execute(sql, values)
        # 返回新插入行的自增 ID，用于关联子表
        return cursor.lastrowid
    except Error as e:
        print(f"\n[数据库错误] 插入到表 `{table_name}` 失败: {e}")
        print(f"  - SQL: {sql}")
        print(f"  - Data: {data}")
        raise  # 抛出异常，以便上层进行事务回滚


# ============================= 3. 核心处理逻辑 =============================

def process_and_insert(cursor, json_data, table_name_prefix: str, parent_id=None, parent_table_name=None):
    """
    递归地处理 JSON 数据，并将其插入到对应的数据库表中。

    :param cursor: 数据库游标
    :param json_data: 要处理的 JSON 对象或列表
    :param table_name_prefix: 表名的前缀 (如 'base_info', 'certifications')
    :param parent_id: 父记录在数据库中的 ID
    :param parent_table_name: 父表的全名 (如 'base_info')
    """
    if isinstance(json_data, list):
        # 如果是列表，遍历其中每个元素并递归处理
        for item in json_data:
            process_and_insert(cursor, item, table_name_prefix, parent_id, parent_table_name)
        return

    if not isinstance(json_data, dict):
        # 如果不是字典或列表，则无法处理
        return

    # 1. 分离简单字段和复杂字段 (列表/对象)
    simple_fields = {}
    complex_fields = {}

    for key, value in json_data.items():
        if isinstance(value, (dict, list)) and value:  # 仅处理非空的对象和列表
            complex_fields[key] = value
        elif not isinstance(value, (dict, list)):  # 处理简单类型
            simple_fields[key] = value

    # 2. 插入当前层级的数据到主表
    current_table_name = to_snake_case(table_name_prefix)

    # 如果存在父ID，需要将外键添加到待插入数据中
    if parent_id and parent_table_name:
        foreign_key_column = f"{to_snake_case(parent_table_name)}_id"
        simple_fields[foreign_key_column] = parent_id

    # 只有在有简单字段时才执行插入
    if not simple_fields:
        return

    # 执行插入并获取新记录的ID
    new_id = insert_data(cursor, current_table_name, simple_fields)
    print(f"    - 插入记录到 `{current_table_name}` (ID: {new_id})")

    # 3. 遍历复杂字段，递归调用自身以处理子表数据
    for key, value in complex_fields.items():
        # 构造子表的名称，如 base_info_staff_list
        child_table_prefix = f"{table_name_prefix}_{key}"
        # 递归处理，传入新创建的记录ID作为父ID
        process_and_insert(cursor, value, child_table_prefix, new_id, current_table_name)


# ============================= 4. 主执行函数 =============================

def main():
    """主执行函数"""
    connection = create_db_connection()
    if not connection:
        return

    cursor = connection.cursor()

    try:
        for company in COMPANIES_TO_PROCESS:
            print(f"\n{'=' * 20} 开始处理公司: {company} {'=' * 20}")

            # 为每个公司遍历需要查询的接口
            for api_id, (table_prefix, chinese_name) in INTERFACE_DICT.items():

                # 从天眼查获取数据
                api_data = fetch_api_data(company, table_prefix,api_id)

                if api_data:
                    # 开始递归插入过程
                    process_and_insert(cursor, api_data, table_prefix)

            # 处理完一个公司的所有接口后，提交事务
            print(f"完成公司 '{company}' 的所有数据处理，提交事务。")
            connection.commit()

    except Exception as e:
        print(f"\n处理过程中发生严重错误: {e}。事务将被回滚。")
        connection.rollback()
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("\n数据库连接已关闭。")


if __name__ == '__main__':
    if   DB_CONFIG['user'] == 'your_username':
        print("[警告] 请先在脚本中配置您的数据库信息 (DB_CONFIG)  ！")
    else:
        main()
