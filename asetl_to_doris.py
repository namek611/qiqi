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
        # The query returns: hostname||'/'||"SID", 'yuanda', 'E_password_s', hostname||':1521/'||"SID", "SID"
        # These are credentials to connect to each specific SID to run get_user_name and then access schema tables.
        sql = """
            SELECT hostname || '/' || "SID" AS host_sid_info,
                   db_user AS ora_user,        -- User that can access DBA_USERS and target schema tables on that SID
                   db_password AS ora_pass,    -- Password for that user
                   hostname || ':' || port || '/' || "SID" AS conn_str,
                   "SID" as sid,
                   project AS project_name_filter -- Added project for potential filtering
            FROM yuanda.dbinfo
            WHERE del = 0 AND project = 'AS' AND sid NOT IN ('scgia')
        """
        # Note: The original query had 'yuanda' and 'E_password_s' hardcoded for user/pass.
        # The table yuanda.dbinfo needs to have appropriate db_user, db_password columns
        # that grant necessary permissions on each target SID.
        # If 'db_user' and 'db_password' columns don't exist, we might need to adjust this logic
        # or assume the 'yuanda' user from config has sysdba-like access to all listed SIDs.
        # For now, I'll assume dbinfo contains 'db_user' and 'db_password' for each SID.
        # If not, we'll need to use config.ORACLE_YUANDA_USER and config.ORACLE_YUANDA_PASSWORD for all.

        logging.debug(f"Executing SQL to get DB info: {sql}")
        cursor.execute(sql)
        listdb_raw = cursor.fetchall()
        logging.info(f"Found {len(listdb_raw)} source databases from dbinfo table.")

        listdb_processed = []
        # Need to know the actual column names from the cursor.description
        # Assuming column names as per the 'AS' aliases in the SQL query
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
                'user_for_schemas': db_user,    # User to connect to this SID for get_user_name & data access
                'passwd_for_schemas': db_passwd,  # Password for this user
                'connstr_for_schemas': db_conn_str, # Connection string for this SID
                'sid_for_naming': db_sid          # SID string for Doris table naming
            })

        return listdb_processed
    except cx_Oracle.Error as e:
        logging.error(f"Oracle error in get_db_info: {e}")
        return []
    except Exception as e: # Catch other potential errors like column name mismatch
        logging.error(f"Generic error in get_db_info: {e}")
        return []
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'conn' in locals() and conn:
            conn.close()
            logging.info("Oracle metadata database connection closed.")


def get_user_name(connect_user, connect_passwd, connect_str):
    """
    获取指定 Oracle 数据库中符合条件的 schema 名称。
    Uses provided credentials to connect to a specific SID.
    """
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
    """
    获取 Oracle 表的详细信息：列定义、主键、唯一键。
    ora_conn: 已经建立的 cx_Oracle 连接对象。
    schema_name: 表所属的 schema。
    table_name_base: 表名（不含 schema）。
    """
    columns = []
    pk_columns = []
    uk_columns = [] # We will capture the columns of the first enabled unique constraint found

    if not ora_conn:
        logging.error(f"Oracle connection not provided to get_oracle_table_details for {schema_name}.{table_name_base}")
        return columns, pk_columns, uk_columns

    try:
        cursor = ora_conn.cursor()

        # 1. Get column details
        # Using ALL_TAB_COLUMNS to get details like data type, length, precision, scale, nullable
        # Also fetching comments for columns if available (ALL_COL_COMMENTS)
        sql_columns = """
            SELECT
                c.COLUMN_NAME,
                c.DATA_TYPE,
                c.DATA_LENGTH,          -- For VARCHAR2, CHAR: length in bytes. For RAW: length in bytes. For LONG, LONG RAW: undefined. For LOBs: length of LOB locator.
                c.CHAR_LENGTH,          -- For VARCHAR2, CHAR: length in characters.
                c.DATA_PRECISION,       -- For NUMBER: precision. For FLOAT: binary precision. For TIMESTAMP WITH TIME ZONE, TIMESTAMP WITH LOCAL TIME ZONE: fractional seconds precision.
                c.DATA_SCALE,           -- For NUMBER: scale. For FLOAT: 0.
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
            # Check if it's a synonym
            syn_check_sql = "SELECT TABLE_OWNER, TABLE_NAME FROM ALL_SYNONYMS WHERE OWNER = :syn_owner AND SYNONYM_NAME = :syn_name"
            cursor.execute(syn_check_sql, syn_owner=schema_name, syn_name=table_name_base)
            syn_target = cursor.fetchone()
            if syn_target:
                logging.info(f"{schema_name}.{table_name_base} is a synonym for {syn_target[0]}.{syn_target[1]}. Retrying with target.")
                return get_oracle_table_details(ora_conn, syn_target[0], syn_target[1]) # Recursive call for synonym target
            else:
                logging.warning(f"No columns found for {schema_name}.{table_name_base} and it's not a known synonym for the current user.")
                return [], [], []


        for row in fetched_cols:
            col_name, data_type, data_len, char_len, data_prec, data_scale, nullable_char, col_comment = row
            # For VARCHAR2/CHAR, use CHAR_LENGTH if available and > 0, otherwise DATA_LENGTH.
            # This is important for multi-byte character sets where DATA_LENGTH is bytes and CHAR_LENGTH is characters.
            actual_length = char_len if data_type in ('VARCHAR2', 'CHAR', 'NVARCHAR2', 'NCHAR') and char_len > 0 else data_len

            columns.append({
                'name': col_name,
                'type': data_type,
                'length': actual_length, # Use character length for relevant types
                'precision': data_prec,
                'scale': data_scale,
                'nullable': nullable_char == 'Y',
                'comment': col_comment
            })
        logging.info(f"Retrieved {len(columns)} column definitions for {schema_name}.{table_name_base}.")

        # 2. Get Primary Key columns
        sql_pk = """
            SELECT ucc.COLUMN_NAME
            FROM ALL_CONSTRAINTS uc
            JOIN ALL_CONS_COLUMNS ucc ON uc.OWNER = ucc.OWNER
                                     AND uc.CONSTRAINT_NAME = ucc.CONSTRAINT_NAME
                                     AND uc.TABLE_NAME = ucc.TABLE_NAME
            WHERE uc.OWNER = :owner_name
              AND uc.TABLE_NAME = :table_name_val
              AND uc.CONSTRAINT_TYPE = 'P'
              AND uc.STATUS = 'ENABLED'
            ORDER BY ucc.POSITION
        """
        logging.debug(f"Executing PK query for {schema_name}.{table_name_base}")
        cursor.execute(sql_pk, owner_name=schema_name, table_name_val=table_name_base)
        for row in cursor.fetchall():
            pk_columns.append(row[0])
        if pk_columns:
            logging.info(f"Primary Key columns for {schema_name}.{table_name_base}: {pk_columns}")
        else:
            logging.info(f"No Primary Key found for {schema_name}.{table_name_base}")

        # 3. Get Unique Key columns (first enabled unique constraint)
        # We need to find one unique constraint name first, then get its columns.
        sql_find_uk_name = """
            SELECT CONSTRAINT_NAME
            FROM ALL_CONSTRAINTS
            WHERE OWNER = :owner_name
              AND TABLE_NAME = :table_name_val
              AND CONSTRAINT_TYPE = 'U'
              AND STATUS = 'ENABLED'
            ORDER BY CONSTRAINT_NAME -- Get a deterministic one if multiple exist
        """
        logging.debug(f"Executing find UK name query for {schema_name}.{table_name_base}")
        cursor.execute(sql_find_uk_name, owner_name=schema_name, table_name_val=table_name_base)
        uk_constraint_name_row = cursor.fetchone()

        if uk_constraint_name_row:
            uk_constraint_name = uk_constraint_name_row[0]
            logging.info(f"Found Unique Constraint: {uk_constraint_name} for {schema_name}.{table_name_base}. Fetching its columns.")
            sql_uk_cols = """
                SELECT COLUMN_NAME
                FROM ALL_CONS_COLUMNS
                WHERE OWNER = :owner_name
                  AND TABLE_NAME = :table_name_val
                  AND CONSTRAINT_NAME = :constraint_name_val
                ORDER BY POSITION
            """
            cursor.execute(sql_uk_cols, owner_name=schema_name, table_name_val=table_name_base, constraint_name_val=uk_constraint_name)
            for row in cursor.fetchall():
                uk_columns.append(row[0])
            if uk_columns:
                logging.info(f"Unique Key columns for {schema_name}.{table_name_base} (constraint {uk_constraint_name}): {uk_columns}")
        else:
            logging.info(f"No enabled Unique Key constraints found for {schema_name}.{table_name_base}")

    except cx_Oracle.DatabaseError as e:
        # Check for specific error codes, e.g., ORA-00942: table or view does not exist
        error_obj, = e.args
        if error_obj.code == 942: # ORA-00942
            logging.warning(f"ORA-00942: Table or view {schema_name}.{table_name_base} does not exist or insufficient privileges.")
        else:
            logging.error(f"Oracle DatabaseError in get_oracle_table_details for {schema_name}.{table_name_base}: {e}")
    except Exception as e:
        logging.error(f"Generic error in get_oracle_table_details for {schema_name}.{table_name_base}: {e}")
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()

    return columns, pk_columns, uk_columns

def oracle_to_doris_type_mapping(ora_type, data_length, data_precision, data_scale):
    """
    将 Oracle 数据类型映射到 Doris 数据类型。
    ora_type: Oracle 数据类型字符串 (e.g., VARCHAR2, NUMBER, DATE).
    data_length: 对于字符类型，是长度；对于RAW，是字节数. (来自 ALL_TAB_COLUMNS.DATA_LENGTH 或 CHAR_LENGTH)
    data_precision: NUMBER类型的精度 (ALL_TAB_COLUMNS.DATA_PRECISION).
    data_scale: NUMBER类型的刻度 (ALL_TAB_COLUMNS.DATA_SCALE).
    """
    logging.debug(f"Mapping Oracle type: {ora_type}, Length: {data_length}, Precision: {data_precision}, Scale: {data_scale}")

    # Handle cases where precision or scale might be None from Oracle dictionary
    data_precision = int(data_precision) if data_precision is not None else None
    data_scale = int(data_scale) if data_scale is not None else None

    if ora_type in ('VARCHAR2', 'CHAR', 'NVARCHAR2', 'NCHAR'):
        # Max VARCHAR length in Doris is typically 65533. Oracle can go up to 4000 bytes/chars (or 32767 with MAX_STRING_SIZE=EXTENDED).
        # If Oracle length exceeds Doris max, might need to use STRING or consider truncation/error.
        # For now, assume length fits.
        # data_length here is char_length for char types from get_oracle_table_details
        if data_length is not None and data_length > 0:
            # Doris VARCHAR max length is 65533. Oracle CLOBs will map to STRING.
            if data_length > 65533:
                 logging.warning(f"Oracle type {ora_type}({data_length}) exceeds Doris VARCHAR max length (65533). Mapping to STRING.")
                 return "STRING"
            return f"VARCHAR({data_length})"
        else: # No length specified, or 0 (should not happen for these types from dict)
            return "STRING"

    elif ora_type == 'NUMBER':
        if data_precision is None and data_scale is None: # NUMBER without P,S -> treat as DOUBLE for max flexibility
            return "DOUBLE"
        if data_scale is not None and data_scale > 0: # Has decimal part
            precision = data_precision if data_precision is not None else 38 # Default precision for DECIMAL if not specified
            scale = data_scale
            # Doris DECIMAL(P,S) max P is 38.
            if precision > 38:
                logging.warning(f"Oracle NUMBER({precision},{scale}) precision exceeds Doris DECIMAL max (38). Clamping to DECIMAL(38,{scale}). Data loss may occur.")
                precision = 38
            if scale > precision : # Scale cannot exceed precision
                logging.warning(f"Oracle NUMBER({precision},{scale}) scale exceeds precision. Adjusting scale to {precision}. Data loss may occur.")
                scale = precision
            return f"DECIMAL({precision},{scale})"
        else: # Integer types (scale is 0 or None)
            precision = data_precision if data_precision is not None else 0 # Treat NUMBER(P) or NUMBER(P,0)
            if precision == 0: # NUMBER or NUMBER(*) without explicit precision, treat as DOUBLE or large decimal
                 return "DOUBLE" # Or DECIMAL(38,0) if integer nature is certain. For safety, DOUBLE.
            elif precision <= 2: # up to 99
                return "TINYINT" # -128 to 127. NUMBER(1) or NUMBER(2)
            elif precision <= 4: # up to 9999
                return "SMALLINT" # -32768 to 32767. NUMBER(3) or NUMBER(4)
            elif precision <= 9: # up to 999,999,999
                return "INT"    # -2,147,483,648 to 2,147,483,647. NUMBER(5) to NUMBER(9)
            elif precision <= 18: # up to 10^18 - 1
                return "BIGINT" # -9,223,372,036,854,775,808 to 9,223,372,036,854,775,807. NUMBER(10) to NUMBER(18)
            elif precision <= 38:
                # Using LARGEINT for Oracle NUMBER(P,0) where 18 < P <= 38
                # Doris LARGEINT is 128-bit signed integer.
                return "LARGEINT"
            else: # Precision > 38, this should ideally map to DECIMAL(P,0) but Doris max P for DECIMAL is 38.
                  # This case indicates an Oracle number too large for precise LARGEINT or DECIMAL representation directly if P > 38.
                logging.warning(f"Oracle NUMBER({data_precision},0) has precision > 38. Mapping to DECIMAL(38,0) or STRING. Consider data implications. Defaulting to STRING for safety.")
                return "STRING" # Or DECIMAL(38,0) with potential overflow. STRING is safer for very large integers.

    elif ora_type == 'DATE': # Oracle DATE contains both date and time
        return "DATETIME"
    elif 'TIMESTAMP' in ora_type: # TIMESTAMP, TIMESTAMP WITH TIME ZONE, TIMESTAMP WITH LOCAL TIME ZONE
        # Doris DATETIMEV2 can store up to 6 decimal places for seconds.
        # Oracle TIMESTAMP precision is for fractional seconds.
        # If data_scale (which holds fractional second precision for TIMESTAMPs) is > 6, there might be loss of sub-microsecond precision.
        precision_for_datetime = data_scale if data_scale is not None and data_scale <=6 else (6 if data_scale is not None and data_scale > 6 else 0) # default to 0 if not specified
        if data_scale is not None and data_scale > 6:
            logging.warning(f"Oracle {ora_type}({data_scale}) has fractional second precision > 6. Doris DATETIMEV2 will store up to 6 decimal places.")
        return f"DATETIMEV2({precision_for_datetime})" if precision_for_datetime > 0 else "DATETIMEV2" # DATETIMEV2 or DATETIMEV2(P)

    elif ora_type in ('CLOB', 'NCLOB', 'LONG', 'XMLTYPE'):
        return "STRING" # Doris STRING type can handle large text data.

    elif ora_type in ('BLOB', 'RAW', 'LONG RAW', 'BFILE'):
        # Doris does not have a native BLOB type. Options:
        # 1. Store as STRING (Base64 encoded). Application needs to handle encode/decode.
        # 2. Skip these columns if not needed.
        # For now, mapping to STRING. This implies the ETL process should handle Base64 encoding if binary data is to be preserved.
        logging.warning(f"Oracle LOB/RAW type {ora_type} mapped to STRING. Binary data will need Base64 encoding during ETL.")
        return "STRING"

    elif ora_type == 'FLOAT': # Oracle FLOAT(binary_precision)
        # Oracle FLOAT precision is binary precision. Doris DOUBLE is IEEE 754 double-precision.
        return "DOUBLE"

    # ROWID, UROWID are Oracle specific, typically not migrated directly.
    elif ora_type in ('ROWID', 'UROWID'):
        logging.warning(f"Oracle type {ora_type} is an address type, typically not migrated directly. Mapping to STRING if it must be included.")
        return "STRING"

    # Interval types
    elif 'INTERVAL YEAR' in ora_type or 'INTERVAL DAY' in ora_type:
        logging.warning(f"Oracle INTERVAL type {ora_type} has no direct equivalent in Doris. Mapping to STRING. Manual conversion/handling will be needed.")
        return "STRING"

    else:
        logging.warning(f"Unmapped Oracle type: {ora_type}. Defaulting to STRING.")
        return "STRING"

def generate_doris_create_table_ddl(doris_table_name, columns_doris_spec, pk_cols_doris, uk_cols_doris, model_type, distribution_keys, sid_for_naming, ora_schema_name, ora_table_name_base):
    """
    生成 Doris 的 CREATE TABLE DDL 语句。
    doris_table_name: 目标 Doris 表名.
    columns_doris_spec: list of dicts, e.g., [{'name': 'col1', 'type': 'INT', 'nullable': True, 'comment': 'some comment'}, ...]
    pk_cols_doris: list of PK column names (lowercase).
    uk_cols_doris: list of UK column names (lowercase).
    model_type: 'UNIQUE KEY' or 'DUPLICATE KEY'.
    distribution_keys: list of column names for distribution (lowercase).
    sid_for_naming: Oracle SID for comment.
    ora_schema_name: Oracle schema name for comment.
    ora_table_name_base: Oracle base table name for comment.
    """
    logging.debug(f"Generating CREATE TABLE DDL for Doris table: {config.DORIS_DB}.{doris_table_name}")

    if not columns_doris_spec:
        logging.error(f"No column specifications provided for Doris table {doris_table_name}. Cannot generate DDL.")
        return None

    col_defs = []
    for col_spec in columns_doris_spec:
        col_def = f"`{col_spec['name']}` {col_spec['type']}"
        # In Doris, UNIQUE KEY model requires value columns to be nullable if they are not part of the unique key.
        # Or, if they are part of unique key, they must be NOT NULL.
        # For DUPLICATE KEY model, nullability is as defined.
        # The PK/UK columns themselves must be NOT NULL for UNIQUE KEY model.
        # For simplicity, if a column is part of PK/UK in a UNIQUE model, it's NOT NULL. Otherwise, respect original nullability.

        is_key_column_in_unique_model = False
        if model_type == 'UNIQUE KEY':
            keys_for_unique = pk_cols_doris if pk_cols_doris else uk_cols_doris
            if col_spec['name'] in keys_for_unique:
                is_key_column_in_unique_model = True

        if is_key_column_in_unique_model: # Key columns in UNIQUE model must be NOT NULL
             col_def += " NOT NULL"
        elif not col_spec.get('nullable', True): # Respect original NOT NULL if not a value col in UNIQUE key or if DUPLICATE model
            col_def += " NOT NULL"

        # Add default value if specified and type supports it, e.g. DEFAULT '' for VARCHAR/STRING
        # For now, not adding default values automatically, can be enhanced.

        if col_spec.get('comment'):
            # Escape single quotes in comments for SQL
            escaped_comment = col_spec['comment'].replace("'", "''")
            col_def += f" COMMENT '{escaped_comment}'"
        col_defs.append(col_def)

    cols_str = ",\n  ".join(col_defs)

    # Define keys based on model type
    key_clause = ""
    if model_type == 'UNIQUE KEY':
        # Determine which set of keys to use (PK preferred over UK)
        actual_unique_keys = pk_cols_doris if pk_cols_doris else uk_cols_doris
        if not actual_unique_keys:
            logging.error(f"UNIQUE KEY model specified for {doris_table_name} but no PK or UK columns found. This is an invalid state.")
            # Fallback: use first column as unique key, though this might be incorrect.
            actual_unique_keys = [columns_doris_spec[0]['name']] if columns_doris_spec else []
            if actual_unique_keys : logging.warning(f"Defaulting UNIQUE KEY for {doris_table_name} to first column: {actual_unique_keys[0]}. Verify this is correct.")
            else:
                logging.error(f"Cannot define UNIQUE KEY for {doris_table_name} as no columns available. DDL generation failed.")
                return None
        key_clause = f"UNIQUE KEY(`{ '`, `'.join(actual_unique_keys) }`)"
        # For UNIQUE KEY model, distribution keys are often the unique key columns themselves if not specified otherwise.
        if not distribution_keys:
            distribution_keys = actual_unique_keys
            logging.info(f"Distribution keys for UNIQUE table {doris_table_name} defaulted to its unique key columns: {distribution_keys}")

    elif model_type == 'DUPLICATE KEY':
        # For DUPLICATE KEY, we can specify sort columns. If not, Doris may pick some.
        # Often, the first few columns or an empty set is used.
        # Using first column as sort key for DUPLICATE model if columns exist.
        sort_cols_for_duplicate = [columns_doris_spec[0]['name']] if columns_doris_spec else []
        if sort_cols_for_duplicate:
            key_clause = f"DUPLICATE KEY(`{ '`, `'.join(sort_cols_for_duplicate) }`)"
        else: # No columns to make a sort key, this is unusual.
            key_clause = "DUPLICATE KEY()" # Empty duplicate key
            logging.warning(f"DUPLICATE KEY for {doris_table_name} defined with no explicit sort columns due to empty column list.")

        # Distribution keys for DUPLICATE KEY model must be specified.
        # If not provided by earlier logic, default to first column.
        if not distribution_keys and columns_doris_spec:
            distribution_keys = [columns_doris_spec[0]['name']]
            logging.info(f"Distribution keys for DUPLICATE table {doris_table_name} defaulted to its first column: {distribution_keys[0]}")

    if not distribution_keys:
        if columns_doris_spec: # Fallback if somehow still no distribution keys
            distribution_keys = [columns_doris_spec[0]['name']]
            logging.warning(f"Distribution keys for {doris_table_name} ultimately defaulted to first column: {distribution_keys[0]}. This should be reviewed.")
        else:
            logging.error(f"Cannot determine distribution keys for {doris_table_name} as no columns are available. DDL generation failed.")
            return None

    dist_by_hash_clause = f"DISTRIBUTED BY HASH(`{ '`, `'.join(distribution_keys) }`)"
    buckets_clause = f"BUCKETS {config.DEFAULT_DORIS_BUCKETS}" # Or make this adaptive

    table_comment_str = f"Source: Oracle SID={sid_for_naming}, Schema={ora_schema_name}, Table={ora_table_name_base}. Synced: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    escaped_table_comment = table_comment_str.replace("'", "''")

    # Properties: replication_num usually for production. For dev, tag.location.default:1 might be used.
    # Using replication_allocation as it's more common with current Doris versions.
    # If your Doris cluster has only one replica, use "replication_num" = "1".
    # Otherwise, for 3 replicas, "replication_num" = "3" or use storage policy.
    # Defaulting to "tag.location.default: 1" which is common for single-node or simple setups.
    properties = [
        f'"comment" = "{escaped_table_comment}"'
    ]
    # Check if 'replication_num' or 'replication_allocation' is in config, otherwise use a default
    if hasattr(config, 'DORIS_REPLICATION_NUM') and config.DORIS_REPLICATION_NUM:
        properties.append(f'"replication_num" = "{config.DORIS_REPLICATION_NUM}"')
    elif hasattr(config, 'DORIS_REPLICATION_ALLOCATION') and config.DORIS_REPLICATION_ALLOCATION:
         properties.append(f'"replication_allocation" = "{config.DORIS_REPLICATION_ALLOCATION}"')
    else: # Default if nothing specified in config
        properties.append('"replication_allocation" = "tag.location.default: 1"')


    # Add storage format property if specified
    if hasattr(config, 'DORIS_STORAGE_FORMAT') and config.DORIS_STORAGE_FORMAT:
        properties.append(f'"storage_format" = "{config.DORIS_STORAGE_FORMAT}"') # e.g., "V2"
    else:
        properties.append('"storage_format" = "V2"') # Default to V2

    properties_str = ",\n  ".join(properties)

    ddl = f"""CREATE TABLE `{config.DORIS_DB}`.`{doris_table_name}` (
  {cols_str}
)
ENGINE=OLAP
{key_clause}
{dist_by_hash_clause} {buckets_clause}
PROPERTIES (
  {properties_str}
);"""
    # ENGINE=OLAP is default but good to be explicit.

    logging.info(f"Generated DDL for {doris_table_name}:\n{ddl}")
    return ddl

def connect_doris_mysql():
    """建立到 Doris FE 的 MySQL 连接用于 DDL 操作。"""
    try:
        conn = mysql.connector.connect(
            host=config.DORIS_FE_HOST_MYSQL,
            port=config.DORIS_FE_PORT_MYSQL,
            user=config.DORIS_USER,
            password=config.DORIS_PASSWORD,
            database=config.DORIS_DB, # Connect to the specific database
            charset='utf8mb4',
            connect_timeout=10 # Add a connection timeout
        )
        if conn.is_connected():
            logging.info(f"Successfully connected to Doris MySQL endpoint: {config.DORIS_FE_HOST_MYSQL}:{config.DORIS_FE_PORT_MYSQL}, DB: {config.DORIS_DB}")
            return conn
        else:
            logging.error(f"Failed to connect to Doris MySQL endpoint (is_connected=False): {config.DORIS_FE_HOST_MYSQL}:{config.DORIS_FE_PORT_MYSQL}")
            return None
    except mysql.connector.Error as err:
        logging.error(f"Error connecting to Doris MySQL endpoint {config.DORIS_FE_HOST_MYSQL}:{config.DORIS_FE_PORT_MYSQL}: {err}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error connecting to Doris MySQL: {e}")
        return None

def execute_doris_ddl(doris_mysql_conn, ddl_statement):
    """在 Doris 中执行 DDL 语句。"""
    if not doris_mysql_conn or not doris_mysql_conn.is_connected():
        # Attempt to reconnect if connection is lost or None
        logging.warning("Doris MySQL connection is not available or not connected. Attempting to reconnect...")
        doris_mysql_conn = connect_doris_mysql()
        if not doris_mysql_conn or not doris_mysql_conn.is_connected():
            logging.error("Reconnect failed. Cannot execute DDL.")
            return False, doris_mysql_conn # Return connection state

    try:
        cursor = doris_mysql_conn.cursor()
        logging.info(f"Executing DDL in Doris: {ddl_statement}")
        # MySQL connector can handle multiple statements separated by semicolons if server supports it.
        # However, for clarity and control, it's often better to send them one by one if they are truly separate operations.
        # Here, a single DDL (like CREATE TABLE or DROP TABLE) is expected.
        cursor.execute(ddl_statement)
        # DDLs are usually auto-committed in MySQL compatible systems like Doris.
        # Explicit commit might not be necessary but doesn't hurt.
        # doris_mysql_conn.commit()
        logging.info(f"DDL statement executed successfully: {ddl_statement.splitlines()[0]}...") # Log first line of DDL
        return True, doris_mysql_conn
    except mysql.connector.Error as err:
        logging.error(f"Error executing DDL in Doris: {err}\nFailed DDL: {ddl_statement}")
        # Check for connection-related errors
        if err.errno == mysql.connector.errorcode.CR_SERVER_GONE_ERROR or \
           err.errno == mysql.connector.errorcode.CR_SERVER_LOST or \
           err.errno == mysql.connector.errorcode.ER_CON_COUNT_ERROR:
            logging.info("Connection to Doris lost, will attempt to reconnect on next DDL.")
            if doris_mysql_conn.is_connected(): doris_mysql_conn.close()
            return False, None # Signal connection is lost
        return False, doris_mysql_conn # Other DDL execution error
    except Exception as e:
        logging.error(f"Unexpected error executing DDL: {e}\nFailed DDL: {ddl_statement}")
        return False, doris_mysql_conn
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()


def stream_load_data_to_doris(doris_host_http, doris_port_http, doris_user, doris_password,
                              doris_db, doris_table_name, data_batch_csv_string,
                              column_names_for_load, stream_load_properties=None):
    """
    使用 Stream Load 将 CSV 格式的数据批量加载到 Doris。
    column_names_for_load: Doris 表中的列名列表，用于 `columns` header。
    stream_load_properties: dict of additional properties for stream load headers.
    """
    if not data_batch_csv_string:
        logging.info(f"No data in batch for {doris_table_name}. Skipping stream load.")
        return True # No data is not an error

    load_url = f"http://{doris_host_http}:{doris_port_http}/api/{doris_db}/{doris_table_name}/_stream_load"

    # Prepare Basic Auth string
    auth_str = f"{doris_user}:{doris_password}"
    # requests.auth.HTTPBasicAuth handles base64 encoding internally.
    # However, some older setups might need explicit base64. For requests, direct tuple is fine.

    headers = {
        # "Authorization": "Basic " + base64.b64encode(auth_str.encode()).decode(), # Manual Basic Auth
        "Expect": "100-continue", # Important for some HTTP servers/proxies
        "Content-Type": "text/plain; charset=UTF-8",
        "format": "csv",
        "column_separator": ",", # Default CSV column separator
        "line_delimiter": "\\n", # Default CSV line delimiter
        "strip_outer_array": "false", # Not used for CSV
        # "max_filter_ratio": "0.05" # Example: Allow 5% dirty data, configure via stream_load_properties
    }

    # Add column mapping if provided - essential if CSV order differs or subset of columns
    if column_names_for_load:
        headers["columns"] = ",".join(f"`{col.strip()}`" for col in column_names_for_load) # Ensure column names are stripped and quoted if needed

    # Merge custom stream load properties from config or call
    custom_props = {}
    if hasattr(config, 'DORIS_STREAM_LOAD_PROPERTIES'):
        custom_props.update(config.DORIS_STREAM_LOAD_PROPERTIES)
    if stream_load_properties:
        custom_props.update(stream_load_properties)

    for key, value in custom_props.items():
        headers[key] = str(value) # Ensure all property values are strings

    logging.info(f"Attempting Stream Load to URL: {load_url} for table {doris_db}.{doris_table_name}. Batch size: {len(data_batch_csv_string)} bytes.")
    # For debugging, can log first few characters of data and headers:
    # logging.debug(f"Stream Load Headers: {headers}")
    # logging.debug(f"Stream Load Data (first 200 chars): {data_batch_csv_string[:200]}")

    try:
        response = requests.put(
            load_url,
            headers=headers,
            data=data_batch_csv_string.encode('utf-8'), # Data should be bytes
            auth=(doris_user, doris_password), # Let requests handle Basic Auth
            timeout=config.DORIS_STREAM_LOAD_TIMEOUT if hasattr(config, 'DORIS_STREAM_LOAD_TIMEOUT') else 300 # Default 5 mins timeout
        )

        # It's good practice to check response content type before trying to parse as JSON
        if 'application/json' in response.headers.get('Content-Type', ''):
            resp_json = response.json()
            logging.debug(f"Stream Load raw JSON response for {doris_table_name}: {json.dumps(resp_json, indent=2)}")
        else: # Fallback if not JSON, though Doris usually returns JSON
            logging.warning(f"Stream Load response for {doris_table_name} was not JSON. Status: {response.status_code}. Text: {response.text[:500]}")
            # If status code indicates success (e.g. 200 OK), but not JSON, might still be a success.
            # Or it could be an HTML error page from a proxy.
            if 200 <= response.status_code < 300:
                 logging.info(f"Stream Load for {doris_table_name} returned HTTP {response.status_code} but non-JSON response. Assuming success based on status code.")
                 return True # Or investigate further based on response.text
            else:
                 response.raise_for_status() # This will raise an HTTPError if status is 4xx or 5xx
                 return False # Should be caught by raise_for_status

        # Process JSON response
        status = resp_json.get("Status")
        if status == "Success":
            logging.info(f"Stream Load Success for {doris_table_name}: "
                         f"TxnId={resp_json.get('TxnId')}, "
                         f"Loaded={resp_json.get('NumberLoadedRows')}, "
                         f"Filtered={resp_json.get('NumberFilteredRows')}, "
                         f"Unselected={resp_json.get('NumberUnselectedRows')}, "
                         f"TotalRows={resp_json.get('NumberTotalRows')}, "
                         f"LoadTimeMs={resp_json.get('LoadTimeMillis')}ms")
            if resp_json.get('NumberFilteredRows', 0) > 0 or resp_json.get('NumberUnselectedRows', 0) > 0:
                logging.warning(f"Some rows were filtered or unselected during Stream Load for {doris_table_name}. ErrorURL: {resp_json.get('ErrorURL')}")
            return True
        elif status == "Publish Timeout":
            # This means data is loaded but FE hasn't received confirmation from all BEs in time.
            # Data is likely okay. TxnId can be used to check `SHOW LOAD WHERE TxnId = ...`
            logging.warning(f"Stream Load for {doris_table_name} resulted in Publish Timeout. "
                            f"TxnId={resp_json.get('TxnId')}. Data may still be loaded. Check Doris logs/SHOW LOAD. "
                            f"Message: {resp_json.get('Message', 'N/A')}")
            return True # Treat as success for now, but requires monitoring.
        elif status == "Label Already Exists":
            # This can happen if a previous attempt with the same label (auto-generated or custom) succeeded or is in progress.
            # If using auto-generated labels by Doris (by not providing "label" header), this is less common.
            # If providing custom labels, ensure they are unique for each load batch.
            logging.warning(f"Stream Load for {doris_table_name} failed: Label Already Exists. "
                            f"TxnId={resp_json.get('TxnId')}. Label='{resp_json.get('Label', 'N/A')}'. "
                            f"Message: {resp_json.get('Message', 'N/A')}")
            # This might be a transient issue if a retry mechanism is in place with new labels.
            # For a single run, this is an issue to investigate.
            return False # Or True if this is acceptable (e.g. data already loaded by that label)
        else: # Other Failures
            logging.error(f"Stream Load failed for {doris_table_name}. Status: {status}. "
                          f"TxnId={resp_json.get('TxnId')}. Label='{resp_json.get('Label', 'N/A')}'. "
                          f"Message: {resp_json.get('Message', 'N/A')}")
            if "ErrorURL" in resp_json:
                logging.error(f"  Error details URL: {resp_json['ErrorURL']}")
            # Log FailMessageList if present (Doris 2.0+)
            if "FailMessageList" in resp_json and resp_json["FailMessageList"]:
                 for fail_msg_item in resp_json["FailMessageList"]:
                     logging.error(f"  Failed row sample: {fail_msg_item.get('ErrorRowSample')} | Reason: {fail_msg_item.get('ErrorMsg')}")

            return False

    except requests.exceptions.Timeout as e:
        logging.error(f"Stream Load request timed out for {doris_table_name}: {e}")
        return False
    except requests.exceptions.ConnectionError as e:
        logging.error(f"Stream Load connection error for {doris_table_name}: {e}")
        return False
    except requests.exceptions.HTTPError as e: # Raised by response.raise_for_status() for 4xx/5xx
        logging.error(f"Stream Load HTTP error for {doris_table_name}: {e.response.status_code} {e.response.reason}. Response: {e.response.text[:500]}")
        return False
    except requests.exceptions.RequestException as e: # Catch-all for other requests issues
        logging.error(f"Generic Stream Load request exception for {doris_table_name}: {e}")
        return False
    except json.JSONDecodeError as e: # If response.json() fails
        logging.error(f"Failed to decode JSON response from Stream Load for {doris_table_name}: {e}. "
                      f"Response Status: {response.status_code if 'response' in locals() else 'N/A'}. "
                      f"Response Text: {response.text[:500] if 'response' in locals() else 'N/A'}")
        return False
    except Exception as e: # Catch any other unexpected errors
        logging.error(f"An unexpected error occurred during stream load for {doris_table_name}: {e}")
        return False

def main():
    logging.info(f"===== Oracle to Doris ETL process started at {datetime.now()} =====")

    source_databases = get_db_info()
    if not source_databases:
        logging.warning("No source databases found from yuanda.dbinfo or error in get_db_info. Exiting.")
        return

    # Initialize Doris MySQL connection for DDL operations
    # This connection will be managed (reconnected if lost) by execute_doris_ddl
    doris_mysql_conn = connect_doris_mysql()
    # No immediate exit if connection fails here, as execute_doris_ddl will try to reconnect.
    # However, if it's None from the start, the first DDL will likely fail if reconnect also fails.

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
                        oracle_q_table_name = f"{schema_name}.\"{oracle_table_name_base}\"" # Qualified for queries, quotes for case-sensitivity if any

                        doris_table_name = f"ods_{sid_for_naming}_{schema_name}_{oracle_table_name_base}".lower().replace(".","_").replace("-","_")
                        logging.info(f"--- Starting sync for Oracle: {oracle_q_table_name} to Doris: {doris_table_name} ---")

                        # 1. Get Oracle table structure
                        ora_columns_desc, ora_pk_cols, ora_uk_cols = get_oracle_table_details(current_oracle_conn, schema_name, oracle_table_name_base)
                        if not ora_columns_desc:
                            logging.warning(f"Could not retrieve column details for {oracle_q_table_name}. Skipping this table.")
                            continue

                        # 2. Convert to Doris column specifications
                        doris_cols_specs = []
                        for ora_col in ora_columns_desc:
                            doris_cols_specs.append({
                                'name': ora_col['name'].lower(), # Doris convention: lowercase
                                'type': oracle_to_doris_type_mapping(ora_col['type'], ora_col.get('length'), ora_col.get('precision'), ora_col.get('scale')),
                                'nullable': ora_col['nullable'],
                                'comment': ora_col.get('comment', '')
                            })

                        # 3. Determine Doris table model and keys
                        # Per requirements: PK or UK -> UNIQUE KEY model, else DUPLICATE KEY
                        pk_cols_doris = [pk.lower() for pk in ora_pk_cols]
                        uk_cols_doris = [uk.lower() for uk in ora_uk_cols]

                        model_type = 'DUPLICATE KEY'
                        distribution_keys_doris = [] # Will be auto-determined if empty by generate_doris_create_table_ddl

                        if pk_cols_doris: # Primary Key exists
                            model_type = 'UNIQUE KEY'
                            distribution_keys_doris = pk_cols_doris # Default distribution to PK for UNIQUE KEY model
                        elif uk_cols_doris: # No PK, but Unique Key exists
                            model_type = 'UNIQUE KEY'
                            distribution_keys_doris = uk_cols_doris # Default distribution to UK

                        logging.info(f"Determined Doris model type: {model_type} for {doris_table_name}.")
                        if distribution_keys_doris: logging.info(f"Proposed distribution keys: {distribution_keys_doris}")

                        # 4. Generate Doris CREATE TABLE DDL
                        create_ddl_stmt = generate_doris_create_table_ddl(
                            doris_table_name, doris_cols_specs,
                            pk_cols_doris, uk_cols_doris, model_type,
                            distribution_keys_doris, # Pass determined or empty list
                            sid_for_naming, schema_name, oracle_table_name_base
                        )
                        if not create_ddl_stmt:
                             logging.error(f"Failed to generate CREATE TABLE DDL for {doris_table_name}. Skipping.")
                             continue

                        # 5. Drop existing Doris table (Requirement: "删除现有的Doris表并重新创建")
                        drop_ddl_stmt = f"DROP TABLE IF EXISTS `{config.DORIS_DB}`.`{doris_table_name}`"
                        logging.info(f"Attempting to drop existing Doris table: {config.DORIS_DB}.{doris_table_name}")

                        ddl_success, doris_mysql_conn = execute_doris_ddl(doris_mysql_conn, drop_ddl_stmt)
                        if not ddl_success:
                            # If drop fails but connection is still alive, log warning and proceed to create.
                            # If connection is lost (doris_mysql_conn is None), create will also fail or try to reconnect.
                            logging.warning(f"Failed to drop Doris table {doris_table_name} or it did not exist. Error may have occurred, or connection lost.")
                        else:
                            logging.info(f"Doris table {doris_table_name} dropped successfully (or did not exist).")

                        # 6. Create Doris table
                        logging.info(f"Attempting to create Doris table: {config.DORIS_DB}.{doris_table_name}")
                        ddl_success, doris_mysql_conn = execute_doris_ddl(doris_mysql_conn, create_ddl_stmt)
                        if not ddl_success:
                            logging.error(f"Failed to create Doris table {doris_table_name}. Skipping data sync for this table.")
                            continue
                        logging.info(f"Doris table {doris_table_name} created successfully.")

                        # 7. Extract data from Oracle and Stream Load to Doris
                        logging.info(f"Starting data extraction from Oracle table: {oracle_q_table_name}")
                        ora_extract_cursor = None
                        try:
                            ora_extract_cursor = current_oracle_conn.cursor()
                            # Use original Oracle column names from ora_columns_desc for SELECT
                            select_cols_str_oracle = ", ".join([f'"{c["name"]}"' for c in ora_columns_desc])
                            data_query_oracle = f"SELECT {select_cols_str_oracle} FROM {schema_name}.\"{oracle_table_name_base}\""

                            logging.debug(f"Executing Oracle data extraction query: {data_query_oracle}")
                            ora_extract_cursor.execute(data_query_oracle)

                            # Doris column names for the 'columns' header in Stream Load (should be lowercase)
                            doris_col_names_for_load_header = [c['name'] for c in doris_cols_specs]

                            rows_processed_count = 0
                            batch_counter = 0
                            while True:
                                batch_counter += 1
                                oracle_records = ora_extract_cursor.fetchmany(config.BATCH_SIZE)
                                if not oracle_records:
                                    break # No more data

                                num_rows_in_batch = len(oracle_records)
                                rows_processed_count += num_rows_in_batch
                                logging.info(f"Fetched batch {batch_counter} ({num_rows_in_batch} rows) from {oracle_q_table_name}. Total fetched: {rows_processed_count}.")

                                # Convert batch to CSV string for Stream Load
                                csv_data_lines_batch = []
                                for record_tuple in oracle_records:
                                    csv_line_values = []
                                    for value in record_tuple:
                                        if value is None:
                                            csv_line_values.append("\\N") # Doris standard for NULL in CSV
                                        elif isinstance(value, datetime):
                                            # Ensure datetime is formatted as Doris expects for DATETIME/DATETIMEV2
                                            csv_line_values.append(value.strftime('%Y-%m-%d %H:%M:%S.%f')[:26] if value.microsecond else value.strftime('%Y-%m-%d %H:%M:%S'))
                                        elif isinstance(value, cx_Oracle.LOB):
                                            # Basic LOB handling: read and escape. Consider large LOBs.
                                            try:
                                                lob_content = value.read()
                                                # Escape common CSV delimiters if they appear in LOB string content
                                                csv_line_values.append(str(lob_content).replace('\n', '\\n').replace(',', '\\,').replace('"', '""'))
                                            except Exception as lob_e:
                                                logging.error(f"Error reading LOB content for {oracle_q_table_name}: {lob_e}. Replacing with empty string.")
                                                csv_line_values.append("") # Or \N if it should be NULL
                                        else:
                                            # Escape common CSV delimiters for other types
                                            csv_line_values.append(str(value).replace('\n', '\\n').replace(',', '\\,').replace('"', '""'))
                                    csv_data_lines_batch.append(",".join(csv_line_values))
                                csv_batch_payload = "\n".join(csv_data_lines_batch)

                                if not stream_load_data_to_doris(
                                    config.DORIS_FE_HOST_HTTP, config.DORIS_FE_PORT_HTTP,
                                    config.DORIS_USER, config.DORIS_PASSWORD, config.DORIS_DB,
                                    doris_table_name, csv_batch_payload, doris_col_names_for_load_header
                                ):
                                    logging.error(f"Stream Load failed for batch {batch_counter} of table {doris_table_name}. Subsequent batches for this table will be skipped.")
                                    break # Stop processing this table on a Stream Load error
                                else:
                                    logging.info(f"Stream Load batch {batch_counter} for {doris_table_name} reported success.")

                            logging.info(f"Finished data extraction and loading for {oracle_q_table_name}. Total rows processed: {rows_processed_count}")

                        except cx_Oracle.Error as ora_err:
                            logging.error(f"Oracle error during data extraction for {oracle_q_table_name}: {ora_err}")
                        except Exception as gen_err:
                            logging.error(f"Generic error during data handling for {oracle_q_table_name}: {gen_err}")
                        finally:
                            if ora_extract_cursor:
                                ora_extract_cursor.close()
                        logging.info(f"--- Finished sync for Oracle: {oracle_q_table_name} to Doris: {doris_table_name} ---")

        except cx_Oracle.Error as ora_conn_err:
            logging.error(f"Failed to connect to Oracle SID {sid_for_naming} (User: {user_for_sid}): {ora_conn_err}. Skipping this database instance.")
        except Exception as e_outer:
            logging.error(f"An unexpected error occurred while processing Oracle SID {sid_for_naming}: {e_outer}")
        finally:
            if current_oracle_conn:
                current_oracle_conn.close()
                logging.info(f"Oracle connection to SID {sid_for_naming} closed.")

    # Close the persistent Doris MySQL connection at the end of all operations
    if doris_mysql_conn and doris_mysql_conn.is_connected():
        doris_mysql_conn.close()
        logging.info("Doris MySQL connection closed at the end of the script.")

    logging.info(f"===== Oracle to Doris ETL process finished at {datetime.now()} =====")

if __name__ == "__main__":
    # Example: Ensure OCI client is initialized if needed, especially for older cx_Oracle or complex setups
    # try:
    #     cx_Oracle.init_oracle_client(lib_dir="/path/to/your/instantclient_XX_Y") # Adjust path as needed
    # except Exception as e:
    #     print(f"Oracle client initialization error (might be ignorable if already configured): {e}")
    #     logging.warning(f"Oracle client initialization error (might be ignorable if already configured): {e}")
    main()
