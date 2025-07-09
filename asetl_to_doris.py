import cx_Oracle
import mysql.connector
import configparser
import sys
from typing import List, Dict, Any


# --- 1. 数据类型映射 (保持不变) ---
def map_oracle_to_doris_type(ora_type: str, precision: int, scale: int) -> str:
    """将Oracle数据类型映射到Doris数据类型。"""
    if ora_type in ('VARCHAR2', 'CHAR', 'NVARCHAR2', 'CLOB'):
        return 'STRING'
    if ora_type == 'NUMBER':
        if scale is not None and scale > 0:
            p = precision or 38
            s = scale or 10
            return f'DECIMALV3({p}, {s})'
        elif scale == 0 or scale is None:
            if precision is not None and precision < 10:
                return 'INT'
            else:
                return 'BIGINT'
    if ora_type.startswith('TIMESTAMP'):
        return 'DATETIME(6)'
    if ora_type == 'DATE':
        return 'DATETIME'
    if ora_type in ('BLOB'):
        print(f"警告: Oracle类型 'BLOB' 暂不支持自动迁移，将映射为STRING。")
        return 'STRING'
    print(f"警告: 未知的Oracle数据类型 '{ora_type}'，将默认映射为 'STRING'。")
    return 'STRING'


# --- 2. Oracle 操作 (使用 cx_Oracle) ---
def get_oracle_table_info(config: configparser.ConfigParser, owner: str, table_name: str) -> List[Dict[str, Any]]:
    """从Oracle获取表结构信息"""
    try:
        # 使用 cx_Oracle.makedsn 来构建连接字符串
        dsn = cx_Oracle.makedsn(config['oracle']['host'], config['oracle']['port'],
                                service_name=config['oracle']['service_name'])
        with cx_Oracle.connect(
                user=config['oracle']['user'],
                password=config['oracle']['password'],
                dsn=dsn
        ) as connection:
            with connection.cursor() as cursor:
                sql = """
                SELECT column_name, data_type, data_precision, data_scale
                FROM ALL_TAB_COLUMNS
                WHERE owner = :owner AND table_name = :table_name
                ORDER BY column_id
                """
                cursor.execute(sql, owner=owner.upper(), table_name=table_name.upper())
                columns_info = []
                # 获取列名以便将结果转为字典
                column_names_in_query = [d[0] for d in cursor.description]
                for row in cursor.fetchall():
                    row_dict = dict(zip(column_names_in_query, row))
                    columns_info.append({
                        'name': row_dict['COLUMN_NAME'],
                        'type': row_dict['DATA_TYPE'],
                        'precision': row_dict['DATA_PRECISION'],
                        'scale': row_dict['DATA_SCALE']
                    })
                if not columns_info:
                    raise ValueError(f"在Oracle中未找到表 '{owner}.{table_name}' 或该表无任何列。")
                return columns_info
    except cx_Oracle.Error as e:
        print(f"连接或查询Oracle时出错: {e}")
        raise


def generate_doris_create_table_ddl(table_name: str, oracle_cols: List[Dict[str, Any]],
                                    doris_primary_key: str = None) -> str:
    """根据Oracle表结构生成Doris的CREATE TABLE语句"""
    doris_cols_str_list = []
    for col in oracle_cols:
        doris_type = map_oracle_to_doris_type(col['type'], col['precision'], col['scale'])
        # 在每列定义前添加两个空格用于缩进
        doris_cols_str_list.append(f"  `{col['name']}` {doris_type}")

    # --- 关键改动在这里 ---
    # 1. 先将列定义用逗号和换行符连接成一个单独的字符串
    final_cols_definition = ',\n'.join(doris_cols_str_list)
    # ----------------------

    if not doris_primary_key and oracle_cols:
        doris_primary_key = oracle_cols[0]['name']
        print(f"警告: 未指定Doris主键，将默认使用第一个字段 '{doris_primary_key}' 作为DUPLICATE KEY和DISTRIBUTED KEY。")

    if not doris_primary_key:
        raise ValueError("无法确定用于Doris表的Key。")

    # 2. 然后将这个处理好的字符串变量放入f-string中
    # 同时修正了PROPERTIES前的空格
    ddl = f"""
CREATE TABLE IF NOT EXISTS `{table_name}` (
{final_cols_definition}
)
DUPLICATE KEY(`{doris_primary_key}`)
DISTRIBUTED BY HASH(`{doris_primary_key}`) BUCKETS auto
PROPERTIES (
    "replication_allocation" = "tag.location.default: 3"
);
"""
    return ddl
# --- 3. Doris DDL 生成 (保持不变) ---



# --- 4. 数据迁移核心逻辑 (使用 mysql.connector) ---
def migrate_data(ora_config: dict, doris_config: dict, ora_owner: str, ora_table: str, batch_size: int = 1000):
    """执行完整的数据迁移流程"""
    # 1. 获取Oracle表结构
    print(f"步骤 1/5: 从Oracle获取表 '{ora_owner}.{ora_table}' 的结构...")
    try:
        ora_cols_info = get_oracle_table_info(ora_config, ora_owner, ora_table)
        print("成功获取表结构。")
    except (ValueError, cx_Oracle.Error) as e:
        print(f"错误: {e}")
        return

    # 2. 生成Doris DDL
    print("\n步骤 2/5: 生成Doris的CREATE TABLE语句...")
    doris_ddl = generate_doris_create_table_ddl(ora_table, ora_cols_info)
    print("--- 生成的Doris DDL如下 ---")
    print(doris_ddl)
    print("--------------------------")

    # 3. 连接Doris并创建表
    print("\n步骤 3/5: 连接Doris并创建表...")
    try:
        doris_conn = mysql.connector.connect(
            host=doris_config['doris']['host'],
            port=doris_config['doris']['port'],
            user=doris_config['doris']['user'],
            password=doris_config['doris']['password'],
            database=doris_config['doris']['database']
        )
        with doris_conn.cursor() as cursor:
            # mysql.connector 支持一次执行多个语句
            for result in cursor.execute(doris_ddl, multi=True):
                pass
        doris_conn.commit()
        print(f"成功在Doris中创建或确认表 '{ora_table}'。")
    except mysql.connector.Error as e:
        print(f"连接或创建Doris表时出错: {e}")
        return

    # 4. 从Oracle读取数据并写入Doris
    print(f"\n步骤 4/5: 开始从Oracle读取数据并分批写入Doris (每批 {batch_size} 条)...")
    try:
        # 准备Doris的INSERT语句
        column_names = [col['name'] for col in ora_cols_info]
        placeholders = ', '.join(['%s'] * len(column_names))
        insert_sql = f"INSERT INTO `{ora_table}` ({', '.join([f'`{name}`' for name in column_names])}) VALUES ({placeholders})"

        # 连接Oracle
        ora_dsn = cx_Oracle.makedsn(ora_config['oracle']['host'], ora_config['oracle']['port'],
                                    service_name=ora_config['oracle']['service_name'])
        with cx_Oracle.connect(user=ora_config['oracle']['user'], password=ora_config['oracle']['password'],
                               dsn=ora_dsn) as ora_conn:
            with ora_conn.cursor() as ora_cursor:
                ora_cursor.execute(f"SELECT * FROM {ora_owner}.{ora_table}")

                total_rows = 0
                while True:
                    rows = ora_cursor.fetchmany(batch_size)
                    if not rows:
                        break

                    with doris_conn.cursor() as doris_cursor:
                        doris_cursor.executemany(insert_sql, rows)
                    doris_conn.commit()

                    total_rows += len(rows)
                    print(f"已成功迁移 {total_rows} 条数据...")

        print(f"\n步骤 5/5: 数据迁移完成！总共迁移了 {total_rows} 条数据。")

    except cx_Oracle.Error as e:
        print(f"从Oracle读取数据时出错: {e}")
    except mysql.connector.Error as e:
        print(f"写入Doris时出错: {e}")
        doris_conn.rollback()
    finally:
        if 'doris_conn' in locals() and doris_conn.is_connected():
            doris_conn.close()
            print("已关闭Doris连接。")


# --- 主程序入口 ---
if __name__ == "__main__":
    config = configparser.ConfigParser()
    try:
        config.read('config.ini')
        if 'oracle' not in config or 'doris' not in config:
            raise FileNotFoundError
    except FileNotFoundError:
        print("错误: 配置文件 'config.ini' 未找到或格式不正确。")
        sys.exit(1)

    if len(sys.argv) != 3:
        print("使用方法: python oracle_to_doris_v2.py <ORACLE_SCHEMA_NAME> <ORACLE_TABLE_NAME>")
        print("示例: python oracle_to_doris_v2.py SCOTT EMP")
        sys.exit(1)

    oracle_schema = sys.argv[1]
    oracle_table = sys.argv[2]

    print(f"准备将Oracle表 '{oracle_schema}.{oracle_table}' 迁移到Doris...")

    migrate_data(config, config, oracle_schema, oracle_table)


if __name__ == "__main__":

    alldb = [list(i) for i in get_db_info()]
    # print(alldb)
    for data in alldb:
        print(data)
        id, name, passwd, connstr = data
        usernamelist = get_user_name(name, passwd, connstr)
        username = [list(i) for i in usernamelist]
        print(username)
        for i in username:
            print(i[0])
            try:
                for year in [2023, 2024, 2025]:
                    table_name=[f'{username}.RPBDDATA1{year}',f'{username}.LSHSXM{year}']
                    doris_table_name=[f'ods_{username}_RPBDDATA1{year}',f'ods_{username}_LSHSXM{year}']
                    

            except Exception as e:
                print(e)

