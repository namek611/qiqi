# asetl_to_doris.py

import cx_Oracle
import mysql.connector # For Doris DDL/DML via MySQL protocol
import requests # For Doris Stream Load
import json
import logging
from datetime import datetime

# Import configurations
try:
    import config
except ImportError:
    logging.error("config.py not found. Please create it with necessary configurations.")
    # Attempt to provide some defaults if config.py is missing for basic operation
    class DefaultConfig:
        DORIS_FE_HOST_MYSQL = '127.0.0.1'
        DORIS_FE_PORT_MYSQL = 9030
        DORIS_FE_HOST_HTTP = '127.0.0.1'
        DORIS_FE_PORT_HTTP = 8030
        DORIS_USER = 'root'
        DORIS_PASSWORD = ''
        DORIS_DB = 'test_db'
        ORACLE_YUANDA_USER = 'your_oracle_user' # Placeholder
        ORACLE_YUANDA_PASSWORD = 'your_oracle_password' # Placeholder
        ORACLE_YUANDA_CONNSTR = 'localhost:1521/XE' # Placeholder
        TABLE_YEARS = [2023]
        TABLE_PATTERNS = ['TABLE_PATTERN{year}']
        LOG_LEVEL = 'INFO'
        LOG_FORMAT = '%(asctime)s - %(levelname)s - %(module)s - %(message)s'
        LOG_FILE = 'asetl_to_doris.log'
        BATCH_SIZE = 10000
        DEFAULT_DORIS_BUCKETS = 10
    config = DefaultConfig()
    logging.warning("config.py not found. Using default placeholder values. Please create and configure config.py.")


# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format=config.LOG_FORMAT,
    handlers=[
        logging.FileHandler(config.LOG_FILE, mode='a'), # Append mode for log file
        logging.StreamHandler()
    ]
)

def get_db_info():
    """
    获取源 Oracle 数据库连接信息。
    连接到 'yuanda' 用户（在 config.py 中定义）以查询 dbinfo 表。
    """
    try:
        logging.info(f"Connecting to Oracle metadata database: {config.ORACLE_YUANDA_CONNSTR} as {config.ORACLE_YUANDA_USER} to get DB list.")
        conn = cx_Oracle.connect(config.ORACLE_YUANDA_USER, config.ORACLE_YUANDA_PASSWORD, config.ORACLE_YUANDA_CONNSTR, encoding="UTF-8", nencoding="UTF-8")
        cursor = conn.cursor()
        sql = """
            SELECT hostname || '/' || "SID" AS host_sid_info,
                   db_user AS ora_user,        -- User that can access DBA_USERS and target schema tables on that SID
                   db_password AS ora_pass,    -- Password for that user
                   hostname || ':' || port || '/' || "SID" AS conn_str,
                   "SID" as sid,
                   project AS project_name_filter
            FROM yuanda.dbinfo
            WHERE del = 0 AND project = 'AS' AND sid NOT IN ('scgia')
        """
        logging.debug(f"Executing SQL to get DB info: {sql}")
        cursor.execute(sql)
        listdb_raw = cursor.fetchall()
        logging.info(f"Found {len(listdb_raw)} source databases from dbinfo table.")

        listdb_processed = []
        colnames = [desc[0].upper() for desc in cursor.description]
        logging.debug(f"DB Info columns: {colnames}")

        idx_ora_user = colnames.index('ORA_USER')
        idx_ora_pass = colnames.index('ORA_PASS')
        idx_conn_str = colnames.index('CONN_STR')
        idx_sid = colnames.index('SID')

        for row in listdb_raw:
            db_user = row[idx_ora_user]
            db_passwd = row[idx_ora_pass]
            db_conn_str = row[idx_conn_str]
            db_sid = row[idx_sid]

            listdb_processed.append({
                'user_for_schemas': db_user,
                'passwd_for_schemas': db_passwd,
                'connstr_for_schemas': db_conn_str,
                'sid_for_naming': db_sid
            })
        return listdb_processed
    except cx_Oracle.Error as e:
        logging.error(f"Oracle error in get_db_info: {e}")
        return []
    except Exception as e:
        logging.error(f"Generic error in get_db_info: {e}")
        return []
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'conn' in locals() and conn:
            conn.close()
            logging.info("Oracle metadata database connection closed.")


def get_user_name(connect_user, connect_passwd, connect_str):
    sql_user_name = """
        SELECT username
        FROM sys.dba_users
        WHERE account_status = 'OPEN'
          AND username LIKE 'LC%'
          AND username NOT LIKE 'LCB%'
          AND username NOT LIKE '%MDM%'
    """
    usernames = []
    try:
        logging.info(f"Connecting to Oracle {connect_str} as {connect_user} to get user names.")
        conn = cx_Oracle.connect(connect_user, connect_passwd, connect_str, encoding="UTF-8", nencoding="UTF-8")
        cursor = conn.cursor()
        logging.debug(f"Executing SQL to get user names: {sql_user_name}")
        cursor.execute(sql_user_name)
        data = cursor.fetchall()
        usernames = [item[0] for item in data]
        logging.info(f"Found {len(usernames)} relevant schemas in {connect_str}: {usernames}")
    except cx_Oracle.Error as e:
        logging.error(f"Oracle error in get_user_name for {connect_str} (user {connect_user}): {e}")
    except Exception as e:
        logging.error(f"Generic error in get_user_name for {connect_str} (user {connect_user}): {e}")
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'conn' in locals() and conn:
            conn.close()
            logging.debug(f"Oracle connection to {connect_str} closed after getting user names.")
    return usernames

def get_oracle_table_details(ora_conn, schema_name, table_name_base):
    columns = []
    pk_columns = []
    uk_columns = []

    if not ora_conn:
        logging.error(f"Oracle connection not provided to get_oracle_table_details for {schema_name}.{table_name_base}")
        return columns, pk_columns, uk_columns

    try:
        cursor = ora_conn.cursor()
        sql_columns = """
            SELECT
                c.COLUMN_NAME,
                c.DATA_TYPE,
                c.DATA_LENGTH,
                c.CHAR_LENGTH,
                c.DATA_PRECISION,
                c.DATA_SCALE,
                c.NULLABLE,
                NVL(cc.COMMENTS, '') AS COLUMN_COMMENT
            FROM ALL_TAB_COLUMNS c
            LEFT JOIN ALL_COL_COMMENTS cc
              ON c.OWNER = cc.OWNER AND c.TABLE_NAME = cc.TABLE_NAME AND c.COLUMN_NAME = cc.COLUMN_NAME
            WHERE c.OWNER = :owner_name
              AND c.TABLE_NAME = :table_name_val
            ORDER BY c.COLUMN_ID
        """
        logging.debug(f"Executing column details query for {schema_name}.{table_name_base}: {sql_columns} with params owner_name={schema_name}, table_name_val={table_name_base}")
        cursor.execute(sql_columns, owner_name=schema_name, table_name_val=table_name_base)
        fetched_cols = cursor.fetchall()

        if not fetched_cols:
            logging.warning(f"Table or view {schema_name}.{table_name_base} not found or no columns retrieved from ALL_TAB_COLUMNS.")
            syn_check_sql = "SELECT TABLE_OWNER, TABLE_NAME FROM ALL_SYNONYMS WHERE OWNER = :syn_owner AND SYNONYM_NAME = :syn_name"
            cursor.execute(syn_check_sql, syn_owner=schema_name, syn_name=table_name_base)
            syn_target = cursor.fetchone()
            if syn_target:
                logging.info(f"{schema_name}.{table_name_base} is a synonym for {syn_target[0]}.{syn_target[1]}. Retrying with target.")
                return get_oracle_table_details(ora_conn, syn_target[0], syn_target[1])
            else:
                logging.warning(f"No columns found for {schema_name}.{table_name_base} and it's not a known synonym.")
                return [], [], []

        for row in fetched_cols:
            col_name, data_type, data_len, char_len, data_prec, data_scale, nullable_char, col_comment = row
            actual_length = char_len if data_type in ('VARCHAR2', 'CHAR', 'NVARCHAR2', 'NCHAR') and char_len > 0 else data_len
            columns.append({
                'name': col_name, 'type': data_type, 'length': actual_length,
                'precision': data_prec, 'scale': data_scale,
                'nullable': nullable_char == 'Y', 'comment': col_comment
            })
        logging.info(f"Retrieved {len(columns)} column definitions for {schema_name}.{table_name_base}.")

        sql_pk = """
            SELECT ucc.COLUMN_NAME FROM ALL_CONSTRAINTS uc
            JOIN ALL_CONS_COLUMNS ucc ON uc.OWNER = ucc.OWNER AND uc.CONSTRAINT_NAME = ucc.CONSTRAINT_NAME AND uc.TABLE_NAME = ucc.TABLE_NAME
            WHERE uc.OWNER = :owner_name AND uc.TABLE_NAME = :table_name_val AND uc.CONSTRAINT_TYPE = 'P' AND uc.STATUS = 'ENABLED' ORDER BY ucc.POSITION
        """
        cursor.execute(sql_pk, owner_name=schema_name, table_name_val=table_name_base)
        pk_columns = [row[0] for row in cursor.fetchall()]
        if pk_columns: logging.info(f"Primary Key for {schema_name}.{table_name_base}: {pk_columns}")
        else: logging.info(f"No PK for {schema_name}.{table_name_base}")

        sql_find_uk_name = "SELECT CONSTRAINT_NAME FROM ALL_CONSTRAINTS WHERE OWNER = :owner_name AND TABLE_NAME = :table_name_val AND CONSTRAINT_TYPE = 'U' AND STATUS = 'ENABLED' ORDER BY CONSTRAINT_NAME"
        cursor.execute(sql_find_uk_name, owner_name=schema_name, table_name_val=table_name_base)
        uk_constraint_name_row = cursor.fetchone()
        if uk_constraint_name_row:
            uk_constraint_name = uk_constraint_name_row[0]
            sql_uk_cols = "SELECT COLUMN_NAME FROM ALL_CONS_COLUMNS WHERE OWNER = :owner_name AND TABLE_NAME = :table_name_val AND CONSTRAINT_NAME = :constraint_name_val ORDER BY POSITION"
            cursor.execute(sql_uk_cols, owner_name=schema_name, table_name_val=table_name_base, constraint_name_val=uk_constraint_name)
            uk_columns = [row[0] for row in cursor.fetchall()]
            if uk_columns: logging.info(f"Unique Key (constraint {uk_constraint_name}) for {schema_name}.{table_name_base}: {uk_columns}")
        else: logging.info(f"No UKs for {schema_name}.{table_name_base}")

    except cx_Oracle.DatabaseError as e:
        error_obj, = e.args
        if error_obj.code == 942:
            logging.warning(f"ORA-00942: Table {schema_name}.{table_name_base} not found or no privileges.")
        else: logging.error(f"Oracle DBError for {schema_name}.{table_name_base}: {e}")
    except Exception as e: logging.error(f"Generic error in get_oracle_table_details for {schema_name}.{table_name_base}: {e}")
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
    return columns, pk_columns, uk_columns

def oracle_to_doris_type_mapping(ora_type, data_length, data_precision, data_scale):
    logging.debug(f"Mapping Oracle type: {ora_type}, Length: {data_length}, Precision: {data_precision}, Scale: {data_scale}")
    data_precision = int(data_precision) if data_precision is not None else None
    data_scale = int(data_scale) if data_scale is not None else None

    if ora_type in ('VARCHAR2', 'CHAR', 'NVARCHAR2', 'NCHAR'):
        if data_length is not None and data_length > 0:
            if data_length > 65533:
                 logging.warning(f"Oracle type {ora_type}({data_length}) > Doris VARCHAR max (65533). Mapping to STRING.")
                 return "STRING"
            return f"VARCHAR({data_length})"
        else: return "STRING"
    elif ora_type == 'NUMBER':
        if data_precision is None and data_scale is None: return "DOUBLE"
        if data_scale is not None and data_scale > 0:
            precision = data_precision if data_precision is not None else 38
            scale = data_scale
            if precision > 38:
                logging.warning(f"Oracle NUMBER({precision},{scale}) P > 38. Clamping to DECIMAL(38,{scale}).")
                precision = 38
            if scale > precision :
                logging.warning(f"Oracle NUMBER({precision},{scale}) S > P. Adjusting S to {precision}.")
                scale = precision
            return f"DECIMAL({precision},{scale})"
        else:
            precision = data_precision if data_precision is not None else 0
            if precision == 0: return "DOUBLE"
            elif precision <= 2: return "TINYINT"
            elif precision <= 4: return "SMALLINT"
            elif precision <= 9: return "INT"
            elif precision <= 18: return "BIGINT"
            elif precision <= 38: return "LARGEINT"
            else:
                logging.warning(f"Oracle NUMBER({data_precision},0) P > 38. Mapping to STRING for safety.")
                return "STRING"
    elif ora_type == 'DATE': return "DATETIME"
    elif 'TIMESTAMP' in ora_type:
        precision_for_datetime = data_scale if data_scale is not None and data_scale <=6 else (6 if data_scale is not None and data_scale > 6 else 0)
        if data_scale is not None and data_scale > 6:
            logging.warning(f"Oracle {ora_type}({data_scale}) fractional sec precision > 6. Doris DATETIMEV2 stores up to 6.")
        return f"DATETIMEV2({precision_for_datetime})" if precision_for_datetime > 0 else "DATETIMEV2"
    elif ora_type in ('CLOB', 'NCLOB', 'LONG', 'XMLTYPE'): return "STRING"
    elif ora_type in ('BLOB', 'RAW', 'LONG RAW', 'BFILE'):
        logging.warning(f"Oracle LOB/RAW type {ora_type} mapped to STRING. Binary data may need Base64 encoding.")
        return "STRING"
    elif ora_type == 'FLOAT': return "DOUBLE"
    elif ora_type in ('ROWID', 'UROWID'):
        logging.warning(f"Oracle type {ora_type} (address type) mapped to STRING.")
        return "STRING"
    elif 'INTERVAL YEAR' in ora_type or 'INTERVAL DAY' in ora_type:
        logging.warning(f"Oracle INTERVAL type {ora_type} mapped to STRING. Manual conversion needed.")
        return "STRING"
    else:
        logging.warning(f"Unmapped Oracle type: {ora_type}. Defaulting to STRING.")
        return "STRING"

def generate_doris_create_table_ddl(doris_table_name, columns_doris_spec, pk_cols_doris, uk_cols_doris, model_type, distribution_keys, sid_for_naming, ora_schema_name, ora_table_name_base):
    """
    生成 Doris 的 CREATE TABLE DDL 语句。
    columns_doris_spec: 初始的Doris列规格列表 (基于Oracle列序).
    Returns:
        tuple: (ddl_string, ordered_column_names_for_load) or (None, None) if failed.
    """
    logging.debug(f"Generating CREATE TABLE DDL for Doris table: {config.DORIS_DB}.{doris_table_name}")

    if not columns_doris_spec:
        logging.error(f"No column specifications provided for Doris table {doris_table_name}. Cannot generate DDL.")
        return None, None

    model_defining_key_col_names = [] # 小写
    if model_type == 'UNIQUE KEY':
        model_defining_key_col_names = pk_cols_doris if pk_cols_doris else uk_cols_doris # pk_cols_doris/uk_cols_doris are already lowercase
        if not model_defining_key_col_names:
            logging.warning(f"UNIQUE KEY model for {doris_table_name} but no PK/UK. Defaulting to first column as key if available.")
            if columns_doris_spec: model_defining_key_col_names = [columns_doris_spec[0]['name'].lower()] # Ensure name is lowercase
            else:
                logging.error(f"Cannot define UNIQUE KEY for {doris_table_name}, no columns. DDL failed.")
                return None, None
    elif model_type == 'DUPLICATE KEY':
        if columns_doris_spec: model_defining_key_col_names = [columns_doris_spec[0]['name'].lower()] # Ensure name is lowercase

    final_ordered_col_specs = []
    processed_col_names_for_ordering = set()
    col_specs_map_by_name = {spec['name'].lower(): spec for spec in columns_doris_spec}

    for key_col_name_lower in model_defining_key_col_names:
        if key_col_name_lower in col_specs_map_by_name:
            final_ordered_col_specs.append(col_specs_map_by_name[key_col_name_lower])
            processed_col_names_for_ordering.add(key_col_name_lower)
        else:
            logging.error(f"Key column '{key_col_name_lower}' defined for model key not found in original column list for {doris_table_name}. Mapped specs: {list(col_specs_map_by_name.keys())}")
            return None, None

    for original_col_spec in columns_doris_spec:
        original_col_name_lower = original_col_spec['name'].lower()
        if original_col_name_lower not in processed_col_names_for_ordering:
            final_ordered_col_specs.append(original_col_spec)

    if not final_ordered_col_specs and columns_doris_spec: # Should not happen if logic is correct
        logging.warning(f"Column reordering logic issue for {doris_table_name}, using original spec order. This may cause DDL errors.")
        final_ordered_col_specs = columns_doris_spec

    col_defs_str_list = []
    final_ordered_col_names_for_load = []

    for col_spec in final_ordered_col_specs:
        col_name_lower = col_spec['name'].lower()
        final_ordered_col_names_for_load.append(col_name_lower)
        col_def_str = f"`{col_name_lower}` {col_spec['type']}"

        is_model_key_col = col_name_lower in model_defining_key_col_names

        if model_type == 'UNIQUE KEY' and is_model_key_col:
            col_def_str += " NOT NULL"
        elif not col_spec.get('nullable', True):
            col_def_str += " NOT NULL"

        if col_spec.get('comment'):
            escaped_comment = col_spec['comment'].replace("'", "''")
            col_def_str += f" COMMENT '{escaped_comment}'"
        col_defs_str_list.append(col_def_str)

    cols_ddl_segment = ",\n  ".join(col_defs_str_list)

    key_clause = ""
    if model_type == 'UNIQUE KEY':
        key_clause = f"UNIQUE KEY(`{ '`, `'.join(model_defining_key_col_names) }`)"
        if not distribution_keys:
            distribution_keys = model_defining_key_col_names # Already lowercase
            logging.info(f"Distribution keys for UNIQUE table {doris_table_name} defaulted to its unique key columns: {distribution_keys}")
    elif model_type == 'DUPLICATE KEY':
        if model_defining_key_col_names:
            key_clause = f"DUPLICATE KEY(`{ '`, `'.join(model_defining_key_col_names) }`)"
        else:
            key_clause = "DUPLICATE KEY()"
        if not distribution_keys and final_ordered_col_specs:
            distribution_keys = [final_ordered_col_specs[0]['name'].lower()]
            logging.info(f"Distribution keys for DUPLICATE table {doris_table_name} defaulted to its first column: {distribution_keys[0]}")

    if not distribution_keys:
        if final_ordered_col_specs:
            distribution_keys = [final_ordered_col_specs[0]['name'].lower()]
            logging.warning(f"Distribution keys for {doris_table_name} ultimately defaulted to first column: {distribution_keys[0]}. Review if optimal.")
        else:
            logging.error(f"Cannot determine distribution keys for {doris_table_name} (no columns). DDL failed.")
            return None, None

    dist_by_hash_clause = f"DISTRIBUTED BY HASH(`{ '`, `'.join(distribution_keys) }`)" # distribution_keys are already lowercase
    buckets_clause = f"BUCKETS {config.DEFAULT_DORIS_BUCKETS}"

    table_comment_str = f"Source: Oracle SID={sid_for_naming}, Schema={ora_schema_name}, Table={ora_table_name_base}. Synced: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    escaped_table_comment = table_comment_str.replace("'", "''")

    properties_list = []
    if hasattr(config, 'DORIS_REPLICATION_NUM') and config.DORIS_REPLICATION_NUM:
        properties_list.append(f'"replication_num" = "{config.DORIS_REPLICATION_NUM}"')
    elif hasattr(config, 'DORIS_REPLICATION_ALLOCATION') and config.DORIS_REPLICATION_ALLOCATION:
         properties_list.append(f'"replication_allocation" = "{config.DORIS_REPLICATION_ALLOCATION}"')
    else:
        properties_list.append('"replication_allocation" = "tag.location.default: 1"')

    if hasattr(config, 'DORIS_STORAGE_FORMAT') and config.DORIS_STORAGE_FORMAT:
        properties_list.append(f'"storage_format" = "{config.DORIS_STORAGE_FORMAT}"')
    else:
        properties_list.append('"storage_format" = "V2"')

    properties_str = ",\n  ".join(properties_list)

    ddl = f"""CREATE TABLE `{config.DORIS_DB}`.`{doris_table_name}` (
  {cols_ddl_segment}
)
ENGINE=OLAP
{key_clause}
{dist_by_hash_clause} {buckets_clause}
PROPERTIES (
  {properties_str}
) COMMENT '{escaped_table_comment}';"""

    logging.info(f"Generated DDL for {doris_table_name}:\n{ddl}")
    logging.info(f"Final ordered column names for Stream Load of {doris_table_name}: {final_ordered_col_names_for_load}")
    return ddl, final_ordered_col_names_for_load


def connect_doris_mysql():
    try:
        conn = mysql.connector.connect(
            host=config.DORIS_FE_HOST_MYSQL, port=config.DORIS_FE_PORT_MYSQL,
            user=config.DORIS_USER, password=config.DORIS_PASSWORD,
            database=config.DORIS_DB, charset='utf8mb4', connect_timeout=10
        )
        if conn.is_connected():
            logging.info(f"Successfully connected to Doris MySQL: {config.DORIS_FE_HOST_MYSQL}:{config.DORIS_FE_PORT_MYSQL}, DB: {config.DORIS_DB}")
            return conn
        else:
            logging.error(f"Failed to connect to Doris MySQL (is_connected=False).")
            return None
    except mysql.connector.Error as err:
        logging.error(f"Error connecting to Doris MySQL: {err}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error connecting to Doris MySQL: {e}")
        return None

def execute_doris_ddl(doris_mysql_conn, ddl_statement):
    if not doris_mysql_conn or not doris_mysql_conn.is_connected():
        logging.warning("Doris MySQL connection unavailable/not connected. Attempting reconnect...")
        doris_mysql_conn = connect_doris_mysql()
        if not doris_mysql_conn or not doris_mysql_conn.is_connected():
            logging.error("Reconnect failed. Cannot execute DDL.")
            return False, doris_mysql_conn
    try:
        cursor = doris_mysql_conn.cursor()
        logging.info(f"Executing DDL in Doris: {ddl_statement.splitlines()[0]}...")
        cursor.execute(ddl_statement)
        logging.info(f"DDL statement executed successfully.")
        return True, doris_mysql_conn
    except mysql.connector.Error as err:
        logging.error(f"Error executing DDL in Doris: {err}\nFailed DDL: {ddl_statement}")
        if err.errno in (mysql.connector.errorcode.CR_SERVER_GONE_ERROR, mysql.connector.errorcode.CR_SERVER_LOST, mysql.connector.errorcode.ER_CON_COUNT_ERROR):
            logging.info("Connection to Doris lost, will attempt reconnect on next DDL.")
            if doris_mysql_conn.is_connected(): doris_mysql_conn.close()
            return False, None
        return False, doris_mysql_conn
    except Exception as e:
        logging.error(f"Unexpected error executing DDL: {e}\nFailed DDL: {ddl_statement}")
        return False, doris_mysql_conn
    finally:
        if 'cursor' in locals() and cursor: cursor.close()

def stream_load_data_to_doris(doris_host_http, doris_port_http, doris_user, doris_password,
                              doris_db, doris_table_name, data_batch_csv_string,
                              column_names_for_load, stream_load_properties=None):
    if not data_batch_csv_string:
        logging.info(f"No data in batch for {doris_table_name}. Skipping stream load.")
        return True

    load_url = f"http://{doris_host_http}:{doris_port_http}/api/{doris_db}/{doris_table_name}/_stream_load"
    headers = {
        "Expect": "100-continue", "Content-Type": "text/plain; charset=UTF-8",
        "format": "csv", "column_separator": ",", "line_delimiter": "\\n",
        "strip_outer_array": "false",
    }
    if column_names_for_load:
        headers["columns"] = ",".join(f"`{col.strip()}`" for col in column_names_for_load)

    custom_props = {}
    if hasattr(config, 'DORIS_STREAM_LOAD_PROPERTIES'):
        custom_props.update(config.DORIS_STREAM_LOAD_PROPERTIES)
    if stream_load_properties: custom_props.update(stream_load_properties)
    for key, value in custom_props.items(): headers[key] = str(value)

    logging.info(f"Attempting Stream Load to {load_url} for {doris_db}.{doris_table_name}. Batch size: {len(data_batch_csv_string)} bytes.")
    try:
        response = requests.put(
            load_url, headers=headers, data=data_batch_csv_string.encode('utf-8'),
            auth=(doris_user, doris_password),
            timeout=getattr(config, 'DORIS_STREAM_LOAD_TIMEOUT', 300)
        )

        if 'application/json' in response.headers.get('Content-Type', ''):
            resp_json = response.json()
            logging.debug(f"Stream Load raw JSON for {doris_table_name}: {json.dumps(resp_json, indent=2)}")
        else:
            logging.warning(f"Stream Load response for {doris_table_name} not JSON. Status: {response.status_code}. Text: {response.text[:500]}")
            if 200 <= response.status_code < 300: return True
            else: response.raise_for_status(); return False

        status = resp_json.get("Status")
        if status == "Success":
            logging.info(f"Stream Load Success for {doris_table_name}: Loaded={resp_json.get('NumberLoadedRows')}, Filtered={resp_json.get('NumberFilteredRows')}")
            if resp_json.get('NumberFilteredRows', 0) > 0: logging.warning(f"Rows filtered in Stream Load for {doris_table_name}. ErrorURL: {resp_json.get('ErrorURL')}")
            return True
        elif status == "Publish Timeout":
            logging.warning(f"Stream Load Publish Timeout for {doris_table_name}. TxnId={resp_json.get('TxnId')}. Data may be loaded. Msg: {resp_json.get('Message', 'N/A')}")
            return True
        elif status == "Label Already Exists":
            logging.warning(f"Stream Load Label Already Exists for {doris_table_name}. TxnId={resp_json.get('TxnId')}. Label='{resp_json.get('Label', 'N/A')}'. Msg: {resp_json.get('Message', 'N/A')}")
            return False
        else:
            logging.error(f"Stream Load failed for {doris_table_name}. Status: {status}. Msg: {resp_json.get('Message', 'N/A')}")
            if "ErrorURL" in resp_json: logging.error(f"  Error details URL: {resp_json['ErrorURL']}")
            if "FailMessageList" in resp_json and resp_json["FailMessageList"]:
                 for item in resp_json["FailMessageList"]: logging.error(f"  Failed row: {item.get('ErrorRowSample')} | Reason: {item.get('ErrorMsg')}")
            return False
    except requests.exceptions.Timeout: logging.error(f"Stream Load request timed out for {doris_table_name}."); return False
    except requests.exceptions.ConnectionError: logging.error(f"Stream Load connection error for {doris_table_name}."); return False
    except requests.exceptions.HTTPError as e: logging.error(f"Stream Load HTTP error for {doris_table_name}: {e.response.status_code} {e.response.reason}. Resp: {e.response.text[:500]}"); return False
    except requests.exceptions.RequestException as e: logging.error(f"Generic Stream Load request exception for {doris_table_name}: {e}"); return False
    except json.JSONDecodeError: logging.error(f"Failed to decode JSON from Stream Load for {doris_table_name}. Status: {response.status_code if 'response' in locals() else 'N/A'}. Text: {response.text[:500] if 'response' in locals() else 'N/A'}"); return False
    except Exception as e: logging.error(f"Unexpected error during stream load for {doris_table_name}: {e}"); return False

def main():
    logging.info(f"===== Oracle to Doris ETL process started at {datetime.now()} =====")
    source_databases = get_db_info()
    if not source_databases:
        logging.warning("No source databases from yuanda.dbinfo or error in get_db_info. Exiting.")
        return

    doris_mysql_conn = connect_doris_mysql()

    for db_info in source_databases:
        user_for_sid = db_info['user_for_schemas']
        passwd_for_sid = db_info['passwd_for_schemas']
        connstr_for_sid = db_info['connstr_for_schemas']
        sid_for_naming = db_info['sid_for_naming']
        logging.info(f"Processing Oracle SID: {sid_for_naming} (ConnStr: {connstr_for_sid}, User: {user_for_sid})")

        schemas_to_process = get_user_name(user_for_sid, passwd_for_sid, connstr_for_sid)
        if not schemas_to_process:
            logging.warning(f"No matching schemas (LC% etc.) found in SID: {sid_for_naming}. Skipping this database.")
            continue

        current_oracle_conn = None
        try:
            logging.info(f"Attempting to connect to Oracle SID {sid_for_naming} for table processing.")
            current_oracle_conn = cx_Oracle.connect(user_for_sid, passwd_for_sid, connstr_for_sid, encoding="UTF-8", nencoding="UTF-8")
            logging.info(f"Successfully connected to Oracle SID {sid_for_naming}.")

            for schema_name in schemas_to_process:
                logging.info(f"Processing Schema: {schema_name} in SID: {sid_for_naming}")
                for year_to_process in config.TABLE_YEARS:
                    for table_name_pattern in config.TABLE_PATTERNS:
                        oracle_table_name_base = table_name_pattern.format(year=year_to_process)
                        oracle_q_table_name = f"{schema_name}.\"{oracle_table_name_base}\""
                        doris_table_name = f"ods_{sid_for_naming}_{schema_name}_{oracle_table_name_base}".lower().replace(".","_").replace("-","_")
                        logging.info(f"--- Starting sync for Oracle: {oracle_q_table_name} to Doris: {doris_table_name} ---")

                        ora_columns_desc, ora_pk_cols, ora_uk_cols = get_oracle_table_details(current_oracle_conn, schema_name, oracle_table_name_base)
                        if not ora_columns_desc:
                            logging.warning(f"Could not retrieve column details for {oracle_q_table_name}. Skipping table.")
                            continue

                        doris_cols_specs = []
                        for ora_col in ora_columns_desc:
                            doris_cols_specs.append({
                                'name': ora_col['name'].lower(),
                                'type': oracle_to_doris_type_mapping(ora_col['type'], ora_col.get('length'), ora_col.get('precision'), ora_col.get('scale')),
                                'nullable': ora_col['nullable'], 'comment': ora_col.get('comment', '')
                            })

                        pk_cols_doris = [pk.lower() for pk in ora_pk_cols]
                        uk_cols_doris = [uk.lower() for uk in ora_uk_cols]
                        model_type = 'DUPLICATE KEY'
                        distribution_keys_doris = []
                        if pk_cols_doris: model_type = 'UNIQUE KEY'; distribution_keys_doris = pk_cols_doris
                        elif uk_cols_doris: model_type = 'UNIQUE KEY'; distribution_keys_doris = uk_cols_doris
                        logging.info(f"Doris model: {model_type} for {doris_table_name}. Proposed dist keys: {distribution_keys_doris if distribution_keys_doris else 'Default'}")

                        # Generate DDL and get ordered columns for load
                        create_ddl_result_tuple = generate_doris_create_table_ddl(
                            doris_table_name, doris_cols_specs,
                            pk_cols_doris, uk_cols_doris, model_type,
                            distribution_keys_doris,
                            sid_for_naming, schema_name, oracle_table_name_base
                        )
                        if not create_ddl_result_tuple or not create_ddl_result_tuple[0]:
                             logging.error(f"Failed to generate CREATE TABLE DDL for {doris_table_name}. Skipping.")
                             continue
                        actual_ddl_for_creation = create_ddl_result_tuple[0]
                        doris_col_names_for_load_header = create_ddl_result_tuple[1]

                        drop_ddl_stmt = f"DROP TABLE IF EXISTS `{config.DORIS_DB}`.`{doris_table_name}`"
                        logging.info(f"Attempting to drop Doris table: {config.DORIS_DB}.{doris_table_name}")
                        ddl_success, doris_mysql_conn = execute_doris_ddl(doris_mysql_conn, drop_ddl_stmt)
                        if not ddl_success: logging.warning(f"Drop failed for {doris_table_name} or it didn't exist.")
                        else: logging.info(f"Doris table {doris_table_name} dropped or did not exist.")

                        logging.info(f"Attempting to create Doris table: {config.DORIS_DB}.{doris_table_name}")
                        ddl_success, doris_mysql_conn = execute_doris_ddl(doris_mysql_conn, actual_ddl_for_creation)
                        if not ddl_success:
                            logging.error(f"Failed to create Doris table {doris_table_name}. Skipping data sync.")
                            continue
                        logging.info(f"Doris table {doris_table_name} created successfully.")

                        logging.info(f"Starting data extraction from Oracle: {oracle_q_table_name}")
                        ora_extract_cursor = None
                        try:
                            ora_extract_cursor = current_oracle_conn.cursor()
                            oracle_cols_for_select_in_doris_order = []
                            oracle_name_map_lower_to_original = {c['name'].lower(): c['name'] for c in ora_columns_desc}
                            missing_oracle_column_for_select = False
                            for doris_col_name_lower in doris_col_names_for_load_header:
                                original_oracle_col_name = oracle_name_map_lower_to_original.get(doris_col_name_lower)
                                if original_oracle_col_name:
                                    oracle_cols_for_select_in_doris_order.append(f'"{original_oracle_col_name}"')
                                else:
                                    logging.error(f"Consistency error: Doris col '{doris_col_name_lower}' not in Oracle map for {oracle_q_table_name}. Map: {oracle_name_map_lower_to_original}. Skipping.")
                                    missing_oracle_column_for_select = True; break
                            if missing_oracle_column_for_select: continue

                            select_cols_str_oracle = ", ".join(oracle_cols_for_select_in_doris_order)
                            data_query_oracle = f"SELECT {select_cols_str_oracle} FROM {schema_name}.\"{oracle_table_name_base}\""
                            logging.debug(f"Executing Oracle data extraction (ordered for Doris DDL): {data_query_oracle}")
                            ora_extract_cursor.execute(data_query_oracle)

                            rows_processed_count = 0; batch_counter = 0
                            while True:
                                batch_counter += 1
                                oracle_records = ora_extract_cursor.fetchmany(config.BATCH_SIZE)
                                if not oracle_records: break
                                num_rows_in_batch = len(oracle_records); rows_processed_count += num_rows_in_batch
                                logging.info(f"Fetched batch {batch_counter} ({num_rows_in_batch} rows) from {oracle_q_table_name}. Total: {rows_processed_count}.")
                                csv_data_lines_batch = []
                                for record_tuple in oracle_records:
                                    csv_line_values = []
                                    for value in record_tuple:
                                        if value is None: csv_line_values.append("\\N")
                                        elif isinstance(value, datetime): csv_line_values.append(value.strftime('%Y-%m-%d %H:%M:%S.%f')[:26] if value.microsecond else value.strftime('%Y-%m-%d %H:%M:%S'))
                                        elif isinstance(value, cx_Oracle.LOB):
                                            try: lob_content = value.read(); csv_line_values.append(str(lob_content).replace('\n', '\\n').replace(',', '\\,').replace('"', '""'))
                                            except Exception as lob_e: logging.error(f"Error reading LOB: {lob_e} for {oracle_q_table_name}. Using empty string."); csv_line_values.append("")
                                        else: csv_line_values.append(str(value).replace('\n', '\\n').replace(',', '\\,').replace('"', '""'))
                                    csv_data_lines_batch.append(",".join(csv_line_values))
                                csv_batch_payload = "\n".join(csv_data_lines_batch)
                                if not stream_load_data_to_doris(
                                    config.DORIS_FE_HOST_HTTP, config.DORIS_FE_PORT_HTTP,
                                    config.DORIS_USER, config.DORIS_PASSWORD, config.DORIS_DB,
                                    doris_table_name, csv_batch_payload, doris_col_names_for_load_header):
                                    logging.error(f"Stream Load failed for batch {batch_counter} of {doris_table_name}. Skipping further batches."); break
                                else: logging.info(f"Stream Load batch {batch_counter} for {doris_table_name} reported success.")
                            logging.info(f"Finished data load for {oracle_q_table_name}. Total rows processed: {rows_processed_count}")
                        except cx_Oracle.Error as ora_err: logging.error(f"Oracle error during data extraction for {oracle_q_table_name}: {ora_err}")
                        except Exception as gen_err: logging.error(f"Generic error during data handling for {oracle_q_table_name}: {gen_err}")
                        finally:
                            if ora_extract_cursor: ora_extract_cursor.close()
                        logging.info(f"--- Finished sync for Oracle: {oracle_q_table_name} to Doris: {doris_table_name} ---")
        except cx_Oracle.Error as ora_conn_err: logging.error(f"Failed to connect to Oracle SID {sid_for_naming} (User: {user_for_sid}): {ora_conn_err}. Skipping.")
        except Exception as e_outer: logging.error(f"Unexpected error processing Oracle SID {sid_for_naming}: {e_outer}")
        finally:
            if current_oracle_conn: current_oracle_conn.close(); logging.info(f"Oracle connection to SID {sid_for_naming} closed.")
    if doris_mysql_conn and doris_mysql_conn.is_connected():
        doris_mysql_conn.close()
        logging.info("Doris MySQL connection closed at script end.")
    logging.info(f"===== Oracle to Doris ETL process finished at {datetime.now()} =====")

if __name__ == "__main__":
    main()

You **must** respond now, using the `message_user` tool.
