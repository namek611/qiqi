import json
import re
from typing import Dict, List, Any
import requests
import sys

# 映射字段类型
TYPE_MAP = {
    "String": "VARCHAR(255)",
    "Number": "BIGINT",
    "Boolean": "BOOLEAN",
    "Date": "DATE", # Assuming date strings will be stored as VARCHAR for flexibility
    "Object": "JSON",
    "Array": "JSON"
}

# 转为 snake_case 命名
def to_snake_case(name):
    name = re.sub(r'([a-z\d])([A-Z])', r'\1_\2', name)
    return name.replace("__", "_").lower()

# 生成字段定义
def gen_column_sql(field_name: str, field_type: str, remark: str, is_primary_key: bool = False, is_foreign_key: bool = False, foreign_key_references: str = "") -> str:
    col_type = TYPE_MAP.get(field_type, "VARCHAR(255)")
    # 从 remark 中移除换行符，避免 SQL 语法错误
    clean_remark = remark.replace('\n', ' ').replace('\r', '') if remark else ''
    column_definition = f"  `{to_snake_case(field_name)}` {col_type}"
    if is_primary_key:
        column_definition += " AUTO_INCREMENT PRIMARY KEY"
    if clean_remark:
        column_definition += f" COMMENT '{clean_remark}'"
    if is_foreign_key and foreign_key_references:
        # Foreign key constraint will be added separately for better compatibility and structure
        pass # Placeholder, actual FK constraint added at table level if needed by design
    return column_definition

def generate_master_table_sql() -> str:
    """
    Generates the SQL CREATE statement for the master 'api_response_items' table.
    """
    columns = [
        gen_column_sql("id", "Number", "主键ID", is_primary_key=True),
        gen_column_sql("company_name", "String", "公司名称"),
        # row_content will be handled by detail tables, so we might not need a JSON blob here if all data goes to detail tables.
        # However, if some row_content is not structured or we want a fallback, it could be included.
        # For now, let's assume detail tables will capture all structured row_content.
        # gen_column_sql("row_content_json", "Object", "原始行数据JSON"),
        gen_column_sql("disabled", "Boolean", "是否禁用"),
        gen_column_sql("last_update_time", "String", "最后更新时间"), # Storing as String due to varying formats or if it's just informational
        gen_column_sql("interface_id", "Number", "接口ID"),
        gen_column_sql("interface_name", "String", "接口名称")
    ]
    table_comment = "API响应条目主表，存储每个API调用返回的基础信息"
    sql = f"CREATE TABLE IF NOT EXISTS `api_response_items` (\n"
    sql += ",\n".join(columns)
    sql += f"\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='{table_comment}';"
    return sql

def get_detail_table_name(interface_table_prefix: str, path: List[str]) -> str:
    """
    Generates a name for a detail table.
    Example: prefix='credit_ratings', path=['items'] -> 'credit_ratings_items_detail'
             prefix='credit_ratings', path=['items', 'some_nested_object'] -> 'credit_ratings_items_some_nested_object_detail'
    """
    effective_path = [p for p in path if p != '_child'] # Remove '_child' from path if it exists
    if not effective_path or effective_path == ['items']: # if path was just 'items' or empty after _child removal
         return to_snake_case(f"{interface_table_prefix}_detail")
    return to_snake_case(f"{interface_table_prefix}_{'_'.join(effective_path)}_detail")


def parse_api_schema_for_detail_tables(
    fields_schema: Dict[str, Any],
    interface_table_prefix: str, # e.g., "credit_ratings" from INTERFACE_DICT
    interface_chinese_name: str, # e.g., "企业信用评级"
    current_path: List[str], # current path in the schema, e.g., ["items", "_child"]
    all_tables_sql: Dict[str, str]
):
    """
    Recursively parses the API's specific schema (like the one from 天眼查 for `row_content`)
    and generates CREATE TABLE SQL for detail tables.
    """
    # Determine the name for the current detail table based on prefix and path
    # We are interested in the structure *inside* 'items._._child._' which corresponds to one item of row_content

    table_name = get_detail_table_name(interface_table_prefix, current_path)

    if table_name not in all_tables_sql:
        columns = [
            gen_column_sql("id", "Number", "主键ID", is_primary_key=True),
            gen_column_sql("master_item_id", "Number", f"外键, 关联 api_response_items.id")
        ]

        table_comment_suffix = " - " + "_".join(current_path) if current_path and current_path != ["items"] else ""
        table_comment = f"{interface_chinese_name}{table_comment_suffix} 详细信息"

        for field_key, field_meta in fields_schema.items():
            if field_key == "_child" and isinstance(field_meta, dict) and field_meta.get("type") == "Object" and "_" in field_meta:
                 # This is a common pattern for lists of objects, recurse into the structure of the object
                parse_api_schema_for_detail_tables(field_meta["_"], interface_table_prefix, interface_chinese_name, current_path, all_tables_sql) # current_path stays same as _child is just a marker
                continue
            elif isinstance(field_meta, dict) and field_meta.get("type") == "Object" and "_" in field_meta:
                # Nested object, create a new detail table for it
                nested_table_path = current_path + [field_key]
                parse_api_schema_for_detail_tables(field_meta["_"], interface_table_prefix, interface_chinese_name, nested_table_path, all_tables_sql)
                # Add a foreign key in the current table to the new nested table (optional, depends on desired E-R model)
                # For simplicity, we'll assume flat structure for now or direct JSON storage for deep nests unless explicitly modeled.
                columns.append(gen_column_sql(field_key, "Object", field_meta.get("remark", "") + " (嵌套对象，存为JSON或关联表)"))
            elif isinstance(field_meta, dict) and field_meta.get("type") == "Array" and "_" in field_meta and "_child" in field_meta["_"] and isinstance(field_meta["_"]["_child"], dict) and "_" in field_meta["_"]["_child"]:
                # Array of complex objects, create a separate table for these items
                array_items_schema = field_meta["_"]["_child"]["_"]
                array_table_path = current_path + [field_key]
                parse_api_schema_for_detail_tables(array_items_schema, interface_table_prefix, interface_chinese_name, array_table_path, all_tables_sql)
                # The link would be: current_table_item -> its_id used as FK in the new array_items_table
            else:
                # Simple field, add as column
                columns.append(gen_column_sql(field_key, field_meta.get("type", "String"), field_meta.get("remark", "")))

        # Remove trailing comma from the last column if any
        sql_columns_str = ",\n".join(columns)

        # Add Foreign Key constraint for master_item_id
        fk_constraint = f"  FOREIGN KEY (`master_item_id`) REFERENCES `api_response_items`(`id`) ON DELETE CASCADE"

        create_table_sql = (
            f"CREATE TABLE IF NOT EXISTS `{table_name}` (\n"
            f"{sql_columns_str},\n"
            f"{fk_constraint}\n"
            f") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='{table_comment}';"
        )
        all_tables_sql[table_name] = create_table_sql

def fetch_api_schema_from_source(api_id: str) -> Dict | None:
    """
    Fetches the API schema structure from the Tianyancha source.
    This is similar to process_api in apijsontosql3.py.
    """
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

        # Navigate to the part of the schema that describes the items in 'row_content'
        # Based on 接口说明.md, this is typically under result.items._._child._
        # Or for simpler structures, it might be result._
        result_node = return_param_dict.get("result", {})
        if not result_node or not isinstance(result_node, dict):
            print(f"警告: API ID {api_id} 的 'result' 节点无效或缺失。", file=sys.stderr)
            return None

        # Try typical path for list items first: result.items._._child._
        items_node = result_node.get("items")
        if items_node and isinstance(items_node, dict) and items_node.get("type") == "Array":
            items_structure = items_node.get("_")
            if items_structure and isinstance(items_structure, dict):
                child_node = items_structure.get("_child")
                if child_node and isinstance(child_node, dict) and child_node.get("type") == "Object":
                    child_fields = child_node.get("_")
                    if child_fields and isinstance(child_fields, dict):
                        print(f"  [信息] API {api_id}: 使用 result.items._._child._ 结构作为 row_content 的schema。")
                        return child_fields # This is the schema for one item in the list

        # Fallback: Try result._ (for APIs like 1001 - base_info, which might not be a list in `result`)
        # This part needs to be flexible based on how `row_content` schema is defined per API.
        # For the actual data `{'err_code': 0, 'items': [{'name': ..., 'row_content': { ACTUAL_DATA_HERE }}]}`,
        # the schema we are fetching here is for `ACTUAL_DATA_HERE`.

        # If `result` itself contains `_` and is an object, it might be the schema.
        # This was the logic in apijsontosql3.py main for some APIs.
        result_underscore_node = result_node.get("_")
        if result_underscore_node:
            if isinstance(result_underscore_node, dict):
                 print(f"  [信息] API {api_id}: 使用 result._ 结构作为 row_content 的schema。")
                 return result_underscore_node
            elif isinstance(result_underscore_node, str): #Handle cases where it's a JSON string
                try:
                    print(f"  [信息] API {api_id}: 解析 result._ 字符串结构作为 row_content 的schema。")
                    return json.loads(result_underscore_node)
                except json.JSONDecodeError:
                    print(f"  [错误] API {api_id}: result._ 字符串无法被解析为JSON。", file=sys.stderr)
                    return None

        # If result_node itself is the schema (no `_` but has fields)
        if not result_underscore_node and all(isinstance(v, dict) and "type" in v for v in result_node.values()):
            print(f"  [信息] API {api_id}: 使用 result 本身作为 row_content 的schema。")
            return result_node

        print(f"警告: API ID {api_id} 未能从获取的schema中定位到 'row_content' 的详细字段定义。检查API文档结构。", file=sys.stderr)
        # print(f"  [调试信息] API {api_id} 'result' 节点内容: {json.dumps(result_node, indent=2, ensure_ascii=False)}", file=sys.stderr)
        return None

    except requests.exceptions.RequestException as e:
        print(f"错误: 请求API ID {api_id} 的schema时发生网络错误: {e}", file=sys.stderr)
        return None
    except (ValueError, json.JSONDecodeError) as e:
        print(f"错误: 处理API ID {api_id} 的schema数据时发生错误: {e}", file=sys.stderr)
        return None


# INTERFACE_DICT should be similar to the one in dataetlinsert.py or apijsontosql3.py
# It maps API IDs to a prefix for their detail tables and a Chinese name.
# Example: {"1049": ("credit_ratings", "企业信用评级"), "884": ("tax_ratings", "税务评级")}
# This should ideally be sourced from a shared configuration or passed in.
# For this script, we'll define a sample one.
DEFAULT_INTERFACE_DICT = {
    "1049": ("credit_ratings", "企业信用评级"),
    "884": ("tax_ratings", "税务评级"),
    "1163": ("person_legal_proceedings", "法律诉讼(人员)"),
    # Add other APIs here as needed, matching `接口说明.md` and `实际返回数据.md`
}

def main(interface_dict_param: Dict[str, tuple[str, str]] = None):
    if interface_dict_param is None:
        interface_dict_param = DEFAULT_INTERFACE_DICT

    all_sql_statements = []
    generated_detail_table_sqls = {} # To store SQL for detail tables, key is table name

    # 1. Generate SQL for the master table
    master_table_sql = generate_master_table_sql()
    all_sql_statements.append(
        "-- ==================================================\n"
        "-- 主表: API响应条目\n"
        "-- ==================================================\n"
        + master_table_sql
    )
    print("已生成主表 `api_response_items` 的SQL。")

    # 2. For each API in the interface_dict, fetch its schema and generate detail table(s)
    for api_id, (table_prefix, chinese_name) in interface_dict_param.items():
        print(f"\n--- 正在处理接口ID: {api_id} ({chinese_name}) ---")

        # Fetch the specific schema for this API's `row_content`
        # This schema corresponds to what's inside the `result.items._._child._` (or similar path) of the API documentation
        row_content_schema = fetch_api_schema_from_source(api_id)

        if row_content_schema:
            # The path used here like ["items"] is a placeholder.
            # The `parse_api_schema_for_detail_tables` will build table names like `credit_ratings_detail`
            # or `credit_ratings_some_list_detail` if there are nested lists within `row_content_schema`.
            # The initial call targets the top-level of `row_content_schema`.
            # We use an empty path `[]` initially for `row_content` as its fields will be directly in `table_prefix_detail`
            parse_api_schema_for_detail_tables(
                fields_schema=row_content_schema,
                interface_table_prefix=table_prefix,
                interface_chinese_name=chinese_name,
                current_path=[], # Path relative to row_content structure
                all_tables_sql=generated_detail_table_sqls
            )
            if not any(table_prefix in k for k in generated_detail_table_sqls.keys()):
                 print(f"  [警告] API {api_id} ({table_prefix}): 未能从获取的 schema 生成对应的详情表SQL。可能是 schema 为空或结构不匹配。")
                 print(f"  [调试信息] row_content_schema for {api_id}: {json.dumps(row_content_schema, indent=2, ensure_ascii=False)}")

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

    # Combine all SQL statements
    final_sql_output = "\n\n".join(all_sql_statements)

    output_filename = "generated_tables_v4.sql"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(final_sql_output)

    print(f"\n\n✅ 所有SQL语句已生成完毕，并保存到文件 `{output_filename}`。")
    if not generated_detail_table_sqls:
        print("⚠️  请注意: 没有生成任何详情表。如果期望有详情表，请检查：")
        print("   1. `DEFAULT_INTERFACE_DICT` 或传入的 `interface_dict_param` 是否包含目标API。")
        print("   2. `fetch_api_schema_from_source` 是否能成功获取并解析这些API的schema。")
        print("   3. 获取到的schema结构是否符合 `parse_api_schema_for_detail_tables` 的预期（例如，包含可识别的字段定义）。")

if __name__ == "__main__":
    # Example of how to run with a specific interface dictionary if needed:
    # custom_interfaces = {
    #     "1049": ("credit_ratings", "企业信用评级"),
    #     # Add more here
    # }
    # main(custom_interfaces)

    # Default run:
    main()
    print("\n提示: `apijsontosql4.py` 生成的SQL用于创建表结构。")
    print("下一步是修改 `dataetlinsert.py` (或创建新脚本) 来填充这些表，")
    print("它需要将实际API响应数据正确地插入到 `api_response_items` 主表，")
    print("并将 `row_content` 部分的数据插入到对应的详情表中。")

# Key changes from apijsontosql3.py:
# 1. Master Table: Introduces a static `api_response_items` master table.
# 2. Detail Tables: Logic for `parse_api_schema_for_detail_tables` is adapted to create tables
#    for the structure within `row_content` of the actual API response. These detail tables
#    are linked to `api_response_items` via a `master_item_id` foreign key.
# 3. Schema Source: `fetch_api_schema_from_source` still gets schema from Tianyancha,
#    but this schema is now understood to define the contents of `row_content`.
# 4. Naming: Detail table names are generated using the interface prefix (e.g., "credit_ratings")
#    and potentially suffixes for nested structures within `row_content`.
# 5. Main Logic: Iterates through an `INTERFACE_DICT` to generate detail tables for each API,
#    in addition to the one master table.
# 6. Chinese Comments: Retains the use of Chinese comments from the schema.
# 7. Path Handling in `parse_api_schema_for_detail_tables`: Simplified and adapted for row_content.
#    The `current_path` helps in naming deeply nested structures if they were to be separate tables.
#    For `row_content` itself, the initial path is empty `[]` so fields appear directly in `xxx_detail` table.

# Assumptions:
# - The schema fetched by `fetch_api_schema_from_source` for a given API ID corresponds to
#   the structure of `row_content` for that API in `实际返回数据.md`.
# - `INTERFACE_DICT` is the source of truth for which APIs to generate detail tables for.
# - Chinese remarks are present in the fetched schema for column comments.
# - Simple one-to-one or one-to-many (from master to detail) relationships. Many-to-many or complex
#   nesting resulting in many tables are simplified (e.g. by storing nested objects as JSON within a detail table column
#   if not explicitly modeled out). The current script aims for one primary detail table per API's row_content.
#   If row_content itself has lists of complex objects, `parse_api_schema_for_detail_tables` attempts to create
#   further linked tables for those.

# Next steps for dataetlinsert.py:
# - When data is fetched:
#   - Insert common fields (name, disabled, last_update_time, interface_id, interface_name) into `api_response_items`. Get the `master_id`.
#   - Based on `interface_id`, take the `row_content` and insert its fields into the corresponding `xxx_detail` table (e.g., `credit_ratings_detail`),
#     using the obtained `master_id` for the `master_item_id` foreign key.
#   - If `row_content` contains nested lists that have their own tables (e.g. `credit_ratings_some_list_detail`),
#     those will also need to be populated with a FK to their parent detail table's ID.
```
