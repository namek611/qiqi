import json
import re
from typing import Dict, List, Any
import requests
import sys
import hashlib

# MySQL表名最大长度 (通常是64，但可以配置)
MYSQL_MAX_TABLE_NAME_LENGTH = 64
TABLE_PREFIX = "ods_"

# 映射字段类型
TYPE_MAP = {
    "String": "VARCHAR(255)",
    "Number": "BIGINT",
    "Boolean": "BOOLEAN",
    "Date": "DATE",
    "Object": "JSON",
    "Array": "JSON"
}

def to_snake_case(name: str) -> str:
    name = re.sub(r'([a-z\d])([A-Z])', r'\1_\2', name)
    return name.replace("__", "_").lower()

def shorten_table_name(name: str, max_length: int = MYSQL_MAX_TABLE_NAME_LENGTH) -> str:
    """
    缩短表名以适应MySQL的长度限制。
    如果名称（包括前缀）超过最大长度，则尝试缩短路径部分，
    并在末尾附加一个短哈希值以保持唯一性。
    """
    if len(name) <= max_length:
        return name

    # 基本策略：如果带前缀后超长，则尝试缩短中间部分
    # ods_very_long_interface_prefix_very_long_path_detail -> ods_very_long_inter...path_det_hash

    prefix_len = len(TABLE_PREFIX)
    core_name = name[prefix_len:] # 移除 ods_ 前缀进行计算

    # 最大核心名称长度
    max_core_len = max_length - prefix_len

    if len(core_name) <= max_core_len: # 如果核心部分没超长（理论上加了ods_才超长）
        return name # 不应该发生，因为上面已经判断过总长

    # 生成一个基于完整核心名称的短哈希 (例如，前5位)
    name_hash = hashlib.md5(core_name.encode('utf-8')).hexdigest()[:5]
    hash_len = len(name_hash) + 1  #  +1 for a '_' separator

    # 可用于实际名称部分的最大长度
    available_len_for_core = max_core_len - hash_len

    if available_len_for_core <= 0:
        # 极端情况，即使加上哈希，前缀本身也太长了 (不太可能)
        # 直接截断加哈希
        return TABLE_PREFIX + core_name[:max_core_len - (len(name_hash))] + name_hash

    # 尝试从中间截断
    # e.g., "very_long_interface_prefix_very_long_path_detail"
    parts = core_name.split('_')
    if len(parts) > 2: # 至少有前缀、路径、后缀
        # 保留部分前缀和部分后缀，中间用... (或直接截断)
        # 简单截断：
        truncated_core = core_name[:available_len_for_core]
        shortened_name = f"{TABLE_PREFIX}{truncated_core}_{name_hash}"
    else: # 如果核心名称部分不多，直接截断
        truncated_core = core_name[:available_len_for_core]
        shortened_name = f"{TABLE_PREFIX}{truncated_core}_{name_hash}"

    # 再次检查确保最终名称不超过最大长度 (理论上应该不会)
    return shortened_name[:max_length]


def get_full_table_name(base_name_without_prefix: str) -> str:
    """
    为基础表名添加ods_前缀并进行可能的缩短。
    """
    prefixed_name = TABLE_PREFIX + base_name_without_prefix
    return shorten_table_name(prefixed_name)


# 生成字段定义
def gen_column_sql(field_name: str, field_type: str, remark: str, is_primary_key: bool = False) -> str:
    col_type = TYPE_MAP.get(field_type, "VARCHAR(255)")
    clean_remark = remark.replace('\n', ' ').replace('\r', '') if remark else ''

    # 主键名统一为 tid
    actual_field_name = "tid" if is_primary_key else to_snake_case(field_name)
    column_definition = f"  `{actual_field_name}` {col_type}"

    if is_primary_key:
        column_definition += " AUTO_INCREMENT PRIMARY KEY"

    if clean_remark:
        column_definition += f" COMMENT '{clean_remark}'"
    return column_definition

def generate_master_table_sql() -> str:
    """
    Generates the SQL CREATE statement for the master table.
    """
    master_table_base_name = "api_response_items"
    actual_master_table_name = get_full_table_name(master_table_base_name)

    columns = [
        gen_column_sql("id", "Number", "主键ID (统一为tid)", is_primary_key=True), # field_name "id" here will be converted to "tid" by gen_column_sql
        gen_column_sql("company_name", "String", "公司名称"),
        gen_column_sql("disabled", "Boolean", "是否禁用"),
        gen_column_sql("last_update_time", "String", "最后更新时间"),
        gen_column_sql("interface_id", "Number", "接口ID"),
        gen_column_sql("interface_name", "String", "接口名称")
    ]
    table_comment = "API响应条目主表，存储每个API调用返回的基础信息"
    sql = f"CREATE TABLE IF NOT EXISTS `{actual_master_table_name}` (\n"
    sql += ",\n".join(columns)
    sql += f"\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='{table_comment}';"
    return sql, actual_master_table_name


def get_detail_table_base_name(interface_table_prefix: str, path: List[str]) -> str:
    """
    Generates a base name (without ods_ prefix) for a detail table.
    """
    effective_path = [p for p in path if p != '_child']
    if not effective_path or effective_path == ['items']:
         # For top-level row_content, table name is based on interface_table_prefix + "_detail"
         base_name = to_snake_case(f"{interface_table_prefix}_detail")
    else:
         base_name = to_snake_case(f"{interface_table_prefix}_{'_'.join(effective_path)}_detail")
    return base_name


def parse_api_schema_for_detail_tables(
    fields_schema: Dict[str, Any],
    interface_table_prefix: str,
    interface_chinese_name: str,
    current_path: List[str],
    all_tables_sql: Dict[str, str],
    master_table_actual_name: str # Actual name of the master table (e.g. ods_api_response_items)
):
    detail_base_name = get_detail_table_base_name(interface_table_prefix, current_path)
    actual_detail_table_name = get_full_table_name(detail_base_name)

    if actual_detail_table_name not in all_tables_sql:
        columns = [
            gen_column_sql("id", "Number", "主键ID (统一为tid)", is_primary_key=True), # Will become `tid`
            # 外键列名应基于主表的主键名 `tid`
            gen_column_sql(f"{master_table_actual_name}_tid", "Number", f"外键, 关联 `{master_table_actual_name}`.tid")
        ]

        table_comment_suffix = " - " + "_".join(current_path) if current_path and current_path != ["items"] else ""
        table_comment = f"{interface_chinese_name}{table_comment_suffix} 详细信息"

        for field_key, field_meta in fields_schema.items():
            # Skip creating a column if the field_key would be 'tid' and it's not the PK (already handled)
            # or if it's the foreign key column name (already handled)
            snake_case_key = to_snake_case(field_key)
            if snake_case_key == "tid" or snake_case_key == f"{master_table_actual_name}_tid":
                # Potentially log a warning if API data field conflicts with reserved names
                print(f"  [警告] 字段 '{field_key}' (转换为 '{snake_case_key}') 与主键或外键名冲突，将跳过为此字段生成专用列。其数据应通过其他方式处理或确保API不使用此字段名。", file=sys.stderr)
                continue

            if field_key == "_child" and isinstance(field_meta, dict) and field_meta.get("type") == "Object" and "_" in field_meta:
                parse_api_schema_for_detail_tables(field_meta["_"], interface_table_prefix, interface_chinese_name, current_path, all_tables_sql, master_table_actual_name)
                continue
            elif isinstance(field_meta, dict) and field_meta.get("type") == "Object" and "_" in field_meta:
                nested_table_path = current_path + [field_key]
                parse_api_schema_for_detail_tables(field_meta["_"], interface_table_prefix, interface_chinese_name, nested_table_path, all_tables_sql, master_table_actual_name)
                columns.append(gen_column_sql(field_key, "Object", field_meta.get("remark", "") + " (嵌套对象，存为JSON或关联子表)"))
            elif isinstance(field_meta, dict) and field_meta.get("type") == "Array" and "_" in field_meta and "_child" in field_meta["_"] and isinstance(field_meta["_"]["_child"], dict) and "_" in field_meta["_"]["_child"]:
                array_items_schema = field_meta["_"]["_child"]["_"]
                array_table_path = current_path + [field_key]
                # For arrays of complex objects, a new detail table is created.
                # Its FK should point back to the current detail table's `tid`.
                parse_api_schema_for_detail_tables(array_items_schema, interface_table_prefix, interface_chinese_name, array_table_path, all_tables_sql, actual_detail_table_name) # Pass current table as master for next level
            else:
                columns.append(gen_column_sql(field_key, field_meta.get("type", "String"), field_meta.get("remark", "")))

        sql_columns_str = ",\n".join(columns)

        # Foreign key pointing to master table (e.g. ods_api_response_items)
        fk_column_name = f"{master_table_actual_name}_tid" # This is how gen_column_sql creates it
        fk_constraint = f"  FOREIGN KEY (`{to_snake_case(fk_column_name)}`) REFERENCES `{master_table_actual_name}`(`tid`) ON DELETE CASCADE"

        create_table_sql = (
            f"CREATE TABLE IF NOT EXISTS `{actual_detail_table_name}` (\n"
            f"{sql_columns_str},\n"
            f"{fk_constraint}\n"
            f") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='{table_comment}';"
        )
        all_tables_sql[actual_detail_table_name] = create_table_sql

def fetch_api_schema_from_source(api_id: str) -> Dict | None:
    url = f"https://open.tianyancha.com/open-admin/interface/uni.json?id={api_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
        "Referer": "https://open.tianyancha.com/",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("data", {})
        return_param_str = data.get("returnParam")
        if not return_param_str:
            print(f"警告: API ID {api_id} 的响应中未找到 'returnParam' 字段。", file=sys.stderr)
            return None

        return_param_dict = json.loads(return_param_str)
        result_node = return_param_dict.get("result", {})
        if not result_node or not isinstance(result_node, dict):
            print(f"警告: API ID {api_id} 的 'result' 节点无效或缺失。", file=sys.stderr)
            return None

        items_node = result_node.get("items")
        if items_node and isinstance(items_node, dict) and items_node.get("type") == "Array":
            items_structure = items_node.get("_")
            if items_structure and isinstance(items_structure, dict):
                child_node = items_structure.get("_child")
                if child_node and isinstance(child_node, dict) and child_node.get("type") == "Object":
                    child_fields = child_node.get("_")
                    if child_fields and isinstance(child_fields, dict):
                        print(f"  [信息] API {api_id}: 使用 result.items._._child._ 结构作为 row_content 的schema。")
                        return child_fields

        result_underscore_node = result_node.get("_")
        if result_underscore_node:
            if isinstance(result_underscore_node, dict):
                 print(f"  [信息] API {api_id}: 使用 result._ 结构作为 row_content 的schema。")
                 return result_underscore_node
            elif isinstance(result_underscore_node, str):
                try:
                    print(f"  [信息] API {api_id}: 解析 result._ 字符串结构作为 row_content 的schema。")
                    return json.loads(result_underscore_node)
                except json.JSONDecodeError:
                    print(f"  [错误] API {api_id}: result._ 字符串无法被解析为JSON。", file=sys.stderr)
                    return None

        if not result_underscore_node and all(isinstance(v, dict) and "type" in v for v in result_node.values()):
            print(f"  [信息] API {api_id}: 使用 result 本身作为 row_content 的schema。")
            return result_node

        print(f"警告: API ID {api_id} 未能从获取的schema中定位到 'row_content' 的详细字段定义。检查API文档结构。", file=sys.stderr)
        return None

    except requests.exceptions.RequestException as e:
        print(f"错误: 请求API ID {api_id} 的schema时发生网络错误: {e}", file=sys.stderr)
        return None
    except (ValueError, json.JSONDecodeError) as e:
        print(f"错误: 处理API ID {api_id} 的schema数据时发生错误: {e}", file=sys.stderr)
        return None

DEFAULT_INTERFACE_DICT = {
    "1049": ("credit_ratings", "企业信用评级"),
    "884": ("tax_ratings", "税务评级"),
    "1163": ("person_legal_proceedings", "法律诉讼(人员)"),
    "9999": ("a_very_long_interface_name_for_testing_abbreviation_rules", "超长接口名称测试缩写规则")
}

def main(interface_dict_param: Dict[str, tuple[str, str]] = None):
    if interface_dict_param is None:
        interface_dict_param = DEFAULT_INTERFACE_DICT

    all_sql_statements = []
    generated_detail_table_sqls = {}

    # 1. Generate SQL for the master table
    master_table_sql, actual_master_table_name = generate_master_table_sql()
    all_sql_statements.append(
        f"-- ==================================================\n"
        f"-- 主表: {actual_master_table_name}\n"
        f"-- ==================================================\n"
        + master_table_sql
    )
    print(f"已生成主表 `{actual_master_table_name}` 的SQL。")

    for api_id, (table_prefix, chinese_name) in interface_dict_param.items():
        print(f"\n--- 正在处理接口ID: {api_id} ({chinese_name}) ---")
        row_content_schema = fetch_api_schema_from_source(api_id)

        if row_content_schema:
            parse_api_schema_for_detail_tables(
                fields_schema=row_content_schema,
                interface_table_prefix=table_prefix,
                interface_chinese_name=chinese_name,
                current_path=[],
                all_tables_sql=generated_detail_table_sqls,
                master_table_actual_name=actual_master_table_name # Pass the actual master table name
            )
            # Check if any table for this prefix was actually generated
            # The key in generated_detail_table_sqls is the full ods_prefixed and shortened name
            was_generated = False
            for generated_table_name in generated_detail_table_sqls.keys():
                # A bit simplistic check, assumes table_prefix is part of the generated name
                # (after ods_ and before _detail or hash)
                if table_prefix in generated_table_name:
                    was_generated = True
                    break
            if not was_generated:
                 print(f"  [警告] API {api_id} ({table_prefix}): 未能从获取的 schema 生成对应的详情表SQL。可能是 schema 为空或结构不匹配。")
                 # print(f"  [调试信息] row_content_schema for {api_id}: {json.dumps(row_content_schema, indent=2, ensure_ascii=False)}")

        else:
            print(f"  [警告] 未能为 API ID {api_id} ({chinese_name}) 获取或解析 `row_content` 的schema，无法生成详情表。")

    if generated_detail_table_sqls:
        all_sql_statements.append(
            "\n-- ==================================================\n"
            "-- 详情表 (Detail Tables for row_content)\n"
            "-- =================================================="
        )
        for table_name, sql_code in generated_detail_table_sqls.items():
            all_sql_statements.append(f"-- SQL for detail table: {table_name}\n{sql_code}")
            print(f"已生成详情表 `{table_name}` 的SQL。")
    else:
        print("\n未生成任何详情表。")

    final_sql_output = "\n\n".join(all_sql_statements)

    output_filename = "generated_tables_v5_ods_tid.sql" # New filename
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(final_sql_output)

    print(f"\n\n✅ 所有SQL语句已生成完毕，并保存到文件 `{output_filename}`。")
    if not generated_detail_table_sqls:
        print("⚠️  请注意: 没有生成任何详情表。如果期望有详情表，请检查相关配置和schema获取。")

if __name__ == "__main__":
    main()
    print("\n提示: `apijsontosql4.py` 生成的SQL已更新：")
    print("  - 所有表名添加 `ods_` 前缀。")
    print("  - 所有表的主键统一为 `tid`。")
    print("  - 长表名会进行缩写处理。")
    print("  - 外键已更新以引用 `tid`。")
    print("下一步是相应修改 `dataetlinsert.py` 以适配这些更改。")
```
