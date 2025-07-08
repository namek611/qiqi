import json
import re
from typing import Dict, List, Any
import requests
import sys
import hashlib

# MySQL表名最大长度 (通常是64，但可以配置)
MYSQL_MAX_TABLE_NAME_LENGTH = 64
TABLE_PREFIX = "ods_"

# 全局列表，用于按顺序存储生成的SQL语句
# ORDERED_SQL_STATEMENTS: List[str] = [] # PEP 526 type hint for global
# PROCESSED_TABLES: set[str] = set()     # PEP 526 type hint for global
ORDERED_SQL_STATEMENTS = []
PROCESSED_TABLES = set()


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

def get_full_table_name(base_name_without_prefix: str) -> str:
    prefixed_name = TABLE_PREFIX + base_name_without_prefix
    return shorten_table_name(prefixed_name)

def gen_column_sql(field_name: str, field_type: str, remark: str, is_primary_key: bool = False) -> str:
    col_type = TYPE_MAP.get(field_type, "VARCHAR(255)")
    clean_remark = remark.replace('\n', ' ').replace('\r', '') if remark else ''
    actual_field_name = "tid" if is_primary_key else to_snake_case(field_name)
    column_definition = f"  `{actual_field_name}` {col_type}"
    if is_primary_key:
        column_definition += " AUTO_INCREMENT PRIMARY KEY"
    if clean_remark:
        column_definition += f" COMMENT '{clean_remark}'"
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
        gen_column_sql("raw_row_content", "Object", "原始的row_content JSON内容") # Object maps to JSON type
    ]
    table_comment = "API响应条目主表，存储每个API调用返回的基础信息及原始row_content"
    sql = f"CREATE TABLE IF NOT EXISTS `{actual_master_table_name}` (\n"
    sql += ",\n".join(columns)
    sql += f"\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='{table_comment}';"
    return sql, actual_master_table_name

def get_detail_table_base_name(interface_table_prefix: str, path: List[str]) -> str:
    effective_path = [p for p in path if p != '_child']
    if not effective_path or effective_path == ['items']:
         base_name = to_snake_case(f"{interface_table_prefix}_detail")
    else:
         base_name = to_snake_case(f"{interface_table_prefix}_{'_'.join(effective_path)}_detail")
    return base_name

def parse_api_schema_for_detail_tables(
    fields_schema: Dict[str, Any],
    interface_table_prefix: str,
    interface_chinese_name: str,
    current_path: List[str],
    master_table_actual_name: str
):
    global ORDERED_SQL_STATEMENTS, PROCESSED_TABLES

    detail_base_name = get_detail_table_base_name(interface_table_prefix, current_path)
    actual_detail_table_name = get_full_table_name(detail_base_name)

    if actual_detail_table_name in PROCESSED_TABLES:
        return

    columns = [
        gen_column_sql("id", "Number", "主键ID (统一为tid)", is_primary_key=True),
        gen_column_sql(f"{master_table_actual_name}_tid", "Number", f"外键, 关联 `{master_table_actual_name}`.tid")
    ]

    recursive_calls_args_list = [] # Store arguments for future recursive calls

    for field_key, field_meta in fields_schema.items():
        snake_case_key = to_snake_case(field_key)
        # Skip if field name conflicts with PK 'tid' or the standard FK name pattern to its master
        if snake_case_key == "tid" or snake_case_key == f"{to_snake_case(master_table_actual_name)}_tid":
            if not (isinstance(field_meta, dict) and field_meta.get("type") == "Object" and "_" in field_meta) and \
               not (isinstance(field_meta, dict) and field_meta.get("type") == "Array" and "_" in field_meta): # allow if it's a complex type that will form a new table
                 print(f"  [警告] 字段 '{field_key}' (转换为 '{snake_case_key}') 与主键或外键名冲突，将跳过为此简单字段生成专用列。", file=sys.stderr)
                 continue

        if field_key == "_child" and isinstance(field_meta, dict) and field_meta.get("type") == "Object" and "_" in field_meta:
            # This case usually means `fields_schema` itself is the item schema of an array.
            # The loop over `fields_schema` directly handles its fields.
            # If `field_meta["_"]` is meant to be a deeper schema, the logic might need adjustment
            # based on the exact API schema's meaning of `_child` at this level.
            # For now, assuming direct processing of fields_schema is correct.
            pass
        elif isinstance(field_meta, dict) and field_meta.get("type") == "Object" and "_" in field_meta:
            nested_table_path = current_path + [field_key]
            # Schedule recursive call for this nested object, it's a child of current table
            recursive_calls_args_list.append({
                "fields_schema": field_meta["_"],
                "interface_table_prefix": interface_table_prefix,
                "interface_chinese_name": interface_chinese_name,
                "current_path": nested_table_path,
                "master_table_actual_name": actual_detail_table_name # Current table is master for this child
            })
            columns.append(gen_column_sql(field_key, "Object", field_meta.get("remark", "") + " (嵌套对象，关联子表或存为JSON)"))
        elif isinstance(field_meta, dict) and field_meta.get("type") == "Array" and "_" in field_meta and \
             "_child" in field_meta["_"] and isinstance(field_meta["_"]["_child"], dict) and "_" in field_meta["_"]["_child"]:
            array_items_schema = field_meta["_"]["_child"]["_"]
            array_table_path = current_path + [field_key]
            # Schedule recursive call for this array of objects, its items form a child table
            recursive_calls_args_list.append({
                "fields_schema": array_items_schema,
                "interface_table_prefix": interface_table_prefix,
                "interface_chinese_name": interface_chinese_name,
                "current_path": array_table_path,
                "master_table_actual_name": actual_detail_table_name # Current table is master for this child
            })
        else:
            columns.append(gen_column_sql(field_key, field_meta.get("type", "String"), field_meta.get("remark", "")))

    table_comment_suffix = " - " + "_".join(current_path) if current_path and current_path != ["items"] else ""
    table_comment = f"{interface_chinese_name}{table_comment_suffix} 详细信息"
    sql_columns_str = ",\n".join(columns)
    fk_column_name_for_master = f"{master_table_actual_name}_tid"
    fk_constraint = f"  FOREIGN KEY (`{to_snake_case(fk_column_name_for_master)}`) REFERENCES `{master_table_actual_name}`(`tid`) ON DELETE CASCADE"

    create_table_sql = (
        f"CREATE TABLE IF NOT EXISTS `{actual_detail_table_name}` (\n"
        f"{sql_columns_str},\n"
        f"{fk_constraint}\n"
        f") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='{table_comment}';"
    )

    # Add current table's SQL to global list *before* processing children
    ORDERED_SQL_STATEMENTS.append(create_table_sql)
    PROCESSED_TABLES.add(actual_detail_table_name)
    print(f"已准备表 `{actual_detail_table_name}` 的SQL。")

    # Now, make the scheduled recursive calls for child tables
    for args_dict in recursive_calls_args_list:
        parse_api_schema_for_detail_tables(**args_dict)

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

        # Path 1: Standard list items directly under result (e.g., result.items._._child._)
        # This is for APIs where 'result' directly contains 'items' array.
        items_node_direct = result_node.get("items")
        if items_node_direct and isinstance(items_node_direct, dict) and items_node_direct.get("type") == "Array":
            items_structure = items_node_direct.get("_")
            if items_structure and isinstance(items_structure, dict):
                child_node = items_structure.get("_child")
                if child_node and isinstance(child_node, dict) and child_node.get("type") == "Object":
                    child_fields = child_node.get("_")
                    if child_fields and isinstance(child_fields, dict):
                        print(f"  [信息] API {api_id}: 使用 result.items._._child._ 结构作为 row_content 的schema。")
                        return child_fields

        # Path 2: Items nested under result._ (e.g., result._.items._._child._)
        # This is for APIs like 1049 where 'result' has a '_' child, and 'items' is under that.
        result_underscore_node = result_node.get("_")
        if result_underscore_node and isinstance(result_underscore_node, dict):
            items_node_nested = result_underscore_node.get("items")
            if items_node_nested and isinstance(items_node_nested, dict) and items_node_nested.get("type") == "Array":
                items_structure = items_node_nested.get("_")
                if items_structure and isinstance(items_structure, dict):
                    child_node = items_structure.get("_child")
                    if child_node and isinstance(child_node, dict) and child_node.get("type") == "Object":
                        child_fields = child_node.get("_")
                        if child_fields and isinstance(child_fields, dict):
                            print(f"  [信息] API {api_id}: 使用 result._.items._._child._ 结构作为 row_content 的schema。")
                            return child_fields

            # Path 3: result._ itself is the schema (and not a wrapper with 'items')
            # This must come after checking for 'items' inside result._
            if not items_node_nested: # If there were no 'items' directly under result._
                # Check if result_underscore_node itself looks like a field schema, not a wrapper
                is_not_wrapper = not ('total' in result_underscore_node and 'items' in result_underscore_node)
                # Further check: ensure it has type definitions, typical for a schema object
                is_schema_like = all(isinstance(v, dict) and "type" in v for v in result_underscore_node.values())

                if is_not_wrapper and is_schema_like and result_underscore_node: # ensure not empty
                    print(f"  [信息] API {api_id}: 使用 result._ 结构作为 row_content 的schema。")
                    return result_underscore_node

        # Path 4: result._ is a JSON string that needs parsing
        if result_underscore_node and isinstance(result_underscore_node, str):
            try:
                # This parsed schema could itself be a wrapper or the direct item schema.
                # For simplicity, we'll assume if it's a string, it's the direct schema.
                # More sophisticated parsing could re-apply checks here.
                parsed_schema_from_string = json.loads(result_underscore_node)
                print(f"  [信息] API {api_id}: 解析 result._ 字符串结构作为 row_content 的schema。")
                # Potentially, this parsed_schema_from_string could also have an 'items' array.
                # For now, we assume it's the direct schema of row_content.
                # A more robust solution might recursively call a schema parsing helper.
                # Example: if parsed_schema_from_string itself has an 'items' key of type Array.
                # items_in_parsed_str = parsed_schema_from_string.get("items")
                # if items_in_parsed_str and isinstance(items_in_parsed_str, dict) and items_in_parsed_str.get("type") == "Array":
                #    ... further drill down ...
                # else: return parsed_schema_from_string

                return parsed_schema_from_string
            except json.JSONDecodeError:
                print(f"  [错误] API {api_id}: result._ 字符串无法被解析为JSON。", file=sys.stderr)
                # Fall through to other checks or final warning

        # Path 5: result itself is the schema (e.g., no '_', no 'items' directly under result)
        # This should be a last resort.
        if not items_node_direct and not result_underscore_node and \
           all(isinstance(v, dict) and "type" in v for v in result_node.values()) and result_node: # ensure not empty
            print(f"  [信息] API {api_id}: 使用 result 本身作为 row_content 的schema。")
            return result_node

        print(f"警告: API ID {api_id} 未能从获取的schema中定位到 'row_content' 的详细字段定义。检查API文档结构。", file=sys.stderr)
        # For debugging, one might print the structure that was not matched:
        # print(f"  [调试信息] API {api_id} result_node: {json.dumps(result_node, indent=2, ensure_ascii=False)}", file=sys.stderr)
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
    "1163": ("person_legal_proceedings", "法律诉讼(人员)"), # This one has a nested array "casePersons"
    "9999": ("a_very_long_interface_name_for_testing_abbreviation_rules", "超长接口名称测试缩写规则")
}

def main(interface_dict_param: Dict[str, tuple[str, str]] = None):
    global ORDERED_SQL_STATEMENTS, PROCESSED_TABLES
    ORDERED_SQL_STATEMENTS = [] # Reset for each run
    PROCESSED_TABLES = set()    # Reset for each run

    if interface_dict_param is None:
        interface_dict_param = DEFAULT_INTERFACE_DICT

    master_table_sql, actual_master_table_name = generate_master_table_sql()
    ORDERED_SQL_STATEMENTS.append(
        f"-- ==================================================\n"
        f"-- 主表: {actual_master_table_name}\n"
        f"-- ==================================================\n"
        + master_table_sql
    )
    PROCESSED_TABLES.add(actual_master_table_name)
    print(f"已生成主表 `{actual_master_table_name}` 的SQL。")

    # Add a header for detail tables section if any detail tables will be generated
    # We'll add it later if ORDERED_SQL_STATEMENTS has more than just the master table part.

    for api_id, (table_prefix, chinese_name) in interface_dict_param.items():
        print(f"\n--- 正在处理接口ID: {api_id} ({chinese_name}) ---")
        row_content_schema = fetch_api_schema_from_source(api_id)

        if row_content_schema:
            # Initial call for the top-level detail table associated with this API's row_content
            parse_api_schema_for_detail_tables(
                fields_schema=row_content_schema,
                interface_table_prefix=table_prefix,
                interface_chinese_name=chinese_name,
                current_path=[],
                master_table_actual_name=actual_master_table_name
            )
        else:
            print(f"  [警告] 未能为 API ID {api_id} ({chinese_name}) 获取或解析 `row_content` 的schema，无法生成详情表。")

    # Construct final SQL output from the ordered list
    # Check if any detail tables were actually prepared (ORDERED_SQL_STATEMENTS will have more than 1 item: master + header)
    # The first item is the master table's header and SQL.
    # If more items exist, they are detail tables.

    final_sql_output_parts = []
    if ORDERED_SQL_STATEMENTS:
        final_sql_output_parts.append(ORDERED_SQL_STATEMENTS[0]) # Master table SQL with its header

        detail_tables_exist = len(ORDERED_SQL_STATEMENTS) > 1
        if detail_tables_exist:
            final_sql_output_parts.append(
                "\n-- ==================================================\n"
                "-- 详情表 (Detail Tables for row_content)\n"
                "-- =================================================="
            )
            # Add SQL for detail tables (all items after the first one)
            for i in range(1, len(ORDERED_SQL_STATEMENTS)):
                 # Extract table name for comment, assuming it's the 3rd word in "CREATE TABLE IF NOT EXISTS `table_name` ("
                sql_statement = ORDERED_SQL_STATEMENTS[i]
                try:
                    table_name_match = re.search(r"CREATE TABLE IF NOT EXISTS `(.*?)` \(", sql_statement)
                    table_name_for_comment = table_name_match.group(1) if table_name_match else "Unknown Detail Table"
                except Exception:
                    table_name_for_comment = "Unknown Detail Table"

                final_sql_output_parts.append(f"-- SQL for detail table: {table_name_for_comment}\n{sql_statement}")
        else:
             print("\n未生成任何详情表。")

    final_sql_output = "\n\n".join(final_sql_output_parts)

    output_filename = "generated_tables_v6_ordered.sql"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(final_sql_output)

    print(f"\n\n✅ 所有SQL语句已按正确依赖顺序生成完毕，并保存到文件 `{output_filename}`。")
    if not detail_tables_exist and len(ORDERED_SQL_STATEMENTS) <=1 : # Check if only master was generated
        print("⚠️  请注意: 没有生成任何详情表。如果期望有详情表，请检查相关配置和schema获取。")


if __name__ == "__main__":
    main()
    print("\n提示: `apijsontosql4.py` 生成的SQL已更新以保证正确的表创建顺序。")
    print("  - 所有表名添加 `ods_` 前缀。")
    print("  - 所有表的主键统一为 `tid`。")
    print("  - 长表名会进行缩写处理。")
    print("  - 外键已更新以引用 `tid`。")
    print("  - 表的创建顺序已调整以满足外键依赖。")
    print("下一步是检查 `dataetlinsert.py` 是否仍与这些结构兼容 (通常是的，除非表名生成方式有意外变化)。")
```
