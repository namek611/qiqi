import json
import re
from typing import Dict, List, Any
import requests
import sys
import hashlib
import os # Added for directory creation

# MySQL表名最大长度 (通常是64，但可以配置)
MYSQL_MAX_TABLE_NAME_LENGTH = 64
TABLE_PREFIX = "ods_"

ORDERED_SQL_STATEMENTS = []
PROCESSED_TABLES = set()

TYPE_MAP = {
    "String": "VARCHAR(255)", "Number": "BIGINT", "Boolean": "BOOLEAN",
    "Date": "DATE", "Object": "JSON", "Array": "JSON"
}

def to_snake_case(name: str) -> str:
    name = re.sub(r'([a-z\d])([A-Z])', r'\1_\2', name)
    return name.replace("__", "_").lower()

def shorten_table_name(name: str, max_length: int = MYSQL_MAX_TABLE_NAME_LENGTH) -> str:
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

def get_full_table_name(base_name_without_prefix: str) -> str:
    prefixed_name = TABLE_PREFIX + base_name_without_prefix
    return shorten_table_name(prefixed_name)

def gen_column_sql(field_name: str, field_type: str, remark: str, is_primary_key: bool = False) -> str:
    col_type = TYPE_MAP.get(field_type, "VARCHAR(255)")
    clean_remark = remark.replace('\n', ' ').replace('\r', '') if remark else ''
    actual_field_name = "tid" if is_primary_key else to_snake_case(field_name)
    column_definition = f"  `{actual_field_name}` {col_type}"
    if is_primary_key: column_definition += " AUTO_INCREMENT PRIMARY KEY"
    if clean_remark: column_definition += f" COMMENT '{clean_remark}'"
    return column_definition

def generate_master_table_sql() -> tuple[str, str]:
    master_table_base_name = "api_response_items"
    actual_master_table_name = get_full_table_name(master_table_base_name)
    columns = [
        gen_column_sql("id", "Number", "主键ID (统一为tid)", is_primary_key=True),
        gen_column_sql("company_name", "String", "公司名称"),
        gen_column_sql("disabled", "Boolean", "是否禁用"),
        gen_column_sql("last_update_time", "String", "最后更新时间"),
        gen_column_sql("interface_id", "Number", "接口ID"),
        gen_column_sql("interface_name", "String", "接口名称"),
        gen_column_sql("raw_row_content", "Object", "原始的row_content JSON内容"),
        "  `is_row_content_processed` BOOLEAN NOT NULL DEFAULT FALSE COMMENT '原始row_content是否已解析并填充到子表'"
    ]
    table_comment = "API响应条目主表，存储每个API调用返回的基础信息、原始row_content及处理状态"
    sql = f"CREATE TABLE IF NOT EXISTS `{actual_master_table_name}` (\n" + ",\n".join(columns) + \
          f"\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='{table_comment}';"
    return sql, actual_master_table_name

def get_detail_table_base_name(interface_table_prefix: str, path: List[str]) -> str:
    effective_path = [p for p in path if p != '_child']
    if not effective_path or effective_path == ['items']:
         return to_snake_case(f"{interface_table_prefix}_detail")
    return to_snake_case(f"{interface_table_prefix}_{'_'.join(effective_path)}_detail")

def parse_api_schema_for_detail_tables(
    fields_schema: Dict[str, Any], interface_table_prefix: str, interface_chinese_name: str,
    current_path: List[str], master_table_actual_name: str
):
    global ORDERED_SQL_STATEMENTS, PROCESSED_TABLES
    detail_base_name = get_detail_table_base_name(interface_table_prefix, current_path)
    actual_detail_table_name = get_full_table_name(detail_base_name)
    if actual_detail_table_name in PROCESSED_TABLES: return

    columns = [
        gen_column_sql("id", "Number", "主键ID (统一为tid)", is_primary_key=True),
        gen_column_sql(f"{master_table_actual_name}_tid", "Number", f"外键, 关联 `{master_table_actual_name}`.tid")
    ]
    recursive_calls_args_list = []
    for field_key, field_meta in fields_schema.items():
        snake_case_key = to_snake_case(field_key)
        if snake_case_key == "tid" or snake_case_key == f"{to_snake_case(master_table_actual_name)}_tid":
            if not (isinstance(field_meta, dict) and field_meta.get("type") == "Object" and "_" in field_meta) and \
               not (isinstance(field_meta, dict) and field_meta.get("type") == "Array" and "_" in field_meta):
                 print(f"  [警告] 字段 '{field_key}' ...与主键或外键名冲突...", file=sys.stderr) # Simplified
                 continue
        if field_key == "_child" and isinstance(field_meta, dict) and field_meta.get("type") == "Object" and "_" in field_meta:
            pass
        elif isinstance(field_meta, dict) and field_meta.get("type") == "Object" and "_" in field_meta:
            recursive_calls_args_list.append({"fields_schema": field_meta["_"], "interface_table_prefix": interface_table_prefix,
                "interface_chinese_name": interface_chinese_name, "current_path": current_path + [field_key],
                "master_table_actual_name": actual_detail_table_name})
            columns.append(gen_column_sql(field_key, "Object", field_meta.get("remark", "") + " (嵌套对象，关联子表或存为JSON)"))
        elif isinstance(field_meta, dict) and field_meta.get("type") == "Array" and "_" in field_meta and \
             "_child" in field_meta["_"] and isinstance(field_meta["_"]["_child"], dict) and "_" in field_meta["_"]["_child"]:
            recursive_calls_args_list.append({"fields_schema": field_meta["_"]["_child"]["_"], "interface_table_prefix": interface_table_prefix,
                "interface_chinese_name": interface_chinese_name, "current_path": current_path + [field_key],
                "master_table_actual_name": actual_detail_table_name})
        else:
            columns.append(gen_column_sql(field_key, field_meta.get("type", "String"), field_meta.get("remark", "")))

    table_comment_suffix = " - " + "_".join(current_path) if current_path and current_path != ["items"] else ""
    table_comment = f"{interface_chinese_name}{table_comment_suffix} 详细信息"
    sql_columns_str = ",\n".join(columns)
    fk_col_name = f"{master_table_actual_name}_tid"
    fk_constraint = f"  FOREIGN KEY (`{to_snake_case(fk_col_name)}`) REFERENCES `{master_table_actual_name}`(`tid`) ON DELETE CASCADE"
    create_table_sql = (f"CREATE TABLE IF NOT EXISTS `{actual_detail_table_name}` (\n{sql_columns_str},\n{fk_constraint}\n"
                       f") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='{table_comment}';")
    ORDERED_SQL_STATEMENTS.append(create_table_sql)
    PROCESSED_TABLES.add(actual_detail_table_name)
    print(f"已准备表 `{actual_detail_table_name}` 的SQL。")
    for args_dict in recursive_calls_args_list: parse_api_schema_for_detail_tables(**args_dict)

def fetch_api_schema_from_source(api_id: str) -> Dict | None:
    url = f"https://open.tianyancha.com/open-admin/interface/uni.json?id={api_id}"
    headers = {"User-Agent": "...", "Referer": "..."} # Simplified for brevity
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("data", {})
        return_param_str = data.get("returnParam")
        if not return_param_str: print(f"警告: API ID {api_id} 无 'returnParam'。", file=sys.stderr); return None
        return_param_dict = json.loads(return_param_str)
        result_node = return_param_dict.get("result", {})
        if not result_node or not isinstance(result_node, dict): print(f"警告: API ID {api_id} 'result'无效。", file=sys.stderr); return None

        # Path finding logic (condensed from previous full version for brevity in overwrite)
        items_direct = result_node.get("items")
        if items_direct and items_direct.get("type") == "Array" and items_direct.get("_",{}).get("_child",{}).get("_"):
            return items_direct["_"]["_child"]["_"] # Path 1

        result_ = result_node.get("_")
        if isinstance(result_, dict):
            items_nested = result_.get("items")
            if items_nested and items_nested.get("type") == "Array" and items_nested.get("_",{}).get("_child",{}).get("_"):
                return items_nested["_"]["_child"]["_"] # Path 2
            if not items_nested and not ('total' in result_ and 'items' in result_): # Path 3
                return result_
        if isinstance(result_, str): # Path 4
            try: return json.loads(result_)
            except json.JSONDecodeError: print(f"错误: API ID {api_id} result._ str 解析失败。", file=sys.stderr)
        if not items_direct and not result_ and result_node: return result_node # Path 5

        print(f"警告: API ID {api_id} 未找到有效schema。", file=sys.stderr); return None
    except Exception as e: print(f"错误: API ID {api_id} schema获取失败: {e}", file=sys.stderr); return None

DEFAULT_INTERFACE_DICT = {
    "1049": ("credit_ratings", "企业信用评级"), "884": ("tax_ratings", "税务评级"),
    "1001": ("base_info", "工商信息"), "1163": ("person_legal_proceedings", "法律诉讼(人员)"),
    "9999": ("a_very_long_interface_name_for_testing_abbreviation_rules", "超长接口名称测试缩写规则")
}

def main(interface_dict_param: Dict[str, tuple[str, str]] = None):
    global ORDERED_SQL_STATEMENTS, PROCESSED_TABLES
    ORDERED_SQL_STATEMENTS = []
    PROCESSED_TABLES = set()

    if interface_dict_param is None: interface_dict_param = DEFAULT_INTERFACE_DICT

    master_table_sql, actual_master_table_name = generate_master_table_sql()
    ORDERED_SQL_STATEMENTS.append(f"-- 主表: {actual_master_table_name}\n{master_table_sql}")
    PROCESSED_TABLES.add(actual_master_table_name)
    print(f"已生成主表 `{actual_master_table_name}` 的SQL。")

    schema_dir = "generated_schemas"
    try:
        os.makedirs(schema_dir, exist_ok=True)
        print(f"Schema存储目录 '{schema_dir}' 已确认/创建。")
    except OSError as e:
        print(f"创建Schema目录 '{schema_dir}' 失败: {e}。不保存schema文件。", file=sys.stderr)
        schema_dir = None

    detail_tables_generated_count = 0
    for api_id, (table_prefix, chinese_name) in interface_dict_param.items():
        print(f"\n--- 正在处理接口ID: {api_id} ({chinese_name}) ---")
        row_content_schema = fetch_api_schema_from_source(api_id)

        if row_content_schema:
            if schema_dir:
                schema_file_path = os.path.join(schema_dir, f"{api_id}.json")
                try:
                    with open(schema_file_path, 'w', encoding='utf-8') as f_schema:
                        json.dump(row_content_schema, f_schema, ensure_ascii=False, indent=4)
                    print(f"  - API ID {api_id} 的 schema 已保存到: {schema_file_path}")
                except Exception as e: # Broad exception for file I/O or JSON issues
                    print(f"  - [错误] 保存 schema 到文件 {schema_file_path} 失败: {e}", file=sys.stderr)

            statements_before = len(ORDERED_SQL_STATEMENTS)
            parse_api_schema_for_detail_tables(row_content_schema, table_prefix, chinese_name, [], actual_master_table_name)
            if len(ORDERED_SQL_STATEMENTS) > statements_before:
                detail_tables_generated_count += (len(ORDERED_SQL_STATEMENTS) - statements_before)
        else:
            print(f"  [警告] 未能为 API ID {api_id} 获取或解析schema，不生成详情表或schema文件。")

    final_sql_output_parts = [ORDERED_SQL_STATEMENTS[0]] # Start with master table
    if detail_tables_generated_count > 0:
        final_sql_output_parts.append("\n-- 详情表 (Detail Tables for row_content)")
        for i in range(1, len(ORDERED_SQL_STATEMENTS)):
            sql_statement = ORDERED_SQL_STATEMENTS[i]
            table_name_match = re.search(r"CREATE TABLE IF NOT EXISTS `(.*?)` \(", sql_statement)
            table_name_for_comment = table_name_match.group(1) if table_name_match else "Unknown"
            final_sql_output_parts.append(f"-- SQL for detail table: {table_name_for_comment}\n{sql_statement}")
    else:
         print("\n未生成任何详情表。")

    final_sql_output = "\n\n".join(final_sql_output_parts)
    output_filename = "generated_tables_v7_schemas_saved.sql"
    with open(output_filename, "w", encoding="utf-8") as f: f.write(final_sql_output)
    print(f"\n\n✅ SQL语句已生成并保存到 `{output_filename}`。")
    if detail_tables_generated_count == 0: print("⚠️  未生成任何详情表。")

if __name__ == "__main__":
    main()
    print("\n提示: `apijsontosql4.py` 现在会将获取到的业务字段schema保存到 `generated_schemas/` 目录下的JSON文件中。")
```
