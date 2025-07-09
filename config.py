# config.py

# Doris Connection Details
DORIS_FE_HOST_MYSQL = '10.50.127.115'
DORIS_FE_PORT_MYSQL = 9030
DORIS_FE_HOST_HTTP = '10.50.127.115' # Assuming HTTP port is on the same host
DORIS_FE_PORT_HTTP = 8030 # Default Doris FE HTTP port
DORIS_USER = 'admin'
DORIS_PASSWORD = 'password' # Please change this in your actual file and do not commit sensitive data
DORIS_DB = 'rsk_data'

# Oracle super user for get_db_info() - if different from schema user
# These are already hardcoded in get_db_info, but good to be aware
ORACLE_YUANDA_USER = 'yuanda'
ORACLE_YUANDA_PASSWORD = 'E_pass_3'
ORACLE_YUANDA_CONNSTR = '10.50.127.9:1521/scgapex'

# Table synchronization settings
TABLE_YEARS = [2023, 2024, 2025] # Confirmed year range
TABLE_PATTERNS = ['RPBDDATA1{year}', 'LSHSXM{year}']

# Logging Configuration
LOG_LEVEL = 'INFO' # e.g., DEBUG, INFO, WARNING, ERROR
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(module)s - %(message)s'
LOG_FILE = 'asetl_to_doris.log'

# Number of rows to fetch/insert in a single batch
# Adjust based on memory and performance
BATCH_SIZE = 10000

# Default number of buckets for Doris tables if not otherwise determined
DEFAULT_DORIS_BUCKETS = 10
