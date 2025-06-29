import json
import re
from typing import Dict
import requests
import sys

# 提供的接口信息字典
INTERFACE_DICT = {
    "1001": ("base_info", "工商信息"),
    "1123": ("suspected_controller", "疑似实际控制人"),
    "1105": ("group_affiliation", "所属集团查询"),
    "880": ("certifications", "资质证书"),
    "998": ("equity_changes", "股权变更"),
    "946": ("suppliers", "供应商"),
    "947": ("customers", "客户"),
    "826": ("financing_history", "融资信息"),
    "967": ("financial_indicators", "财务指标"),
    "884": ("tax_ratings", "税务评级"),
    "943": ("public_sentiment_news", "新闻舆情"),
    "961": ("litigation_filing", "立案信息"),
    "839": ("enforcement_records", "被执行人"),
    "843": ("dishonest_persons", "失信人"),
    "1014": ("consumption_restrictions", "限制消费令"),
    "1036": ("bankruptcy_cases", "破产重整"),
    "1013": ("zhongben_cases", "终本案件"),
    "1163": ("person_legal_proceedings", "法律诉讼(人员)"),
    "1049": ("credit_ratings", "企业信用评级")
}

# 映射字段类型
TYPE_MAP = {
    "String": "VARCHAR(255)",
    "Number": "BIGINT",
    "Boolean": "BOOLEAN",
    "Date": "DATE",
    "Object": "JSON",
    "Array": "JSON"
}


# 转为 snake_case 命名
def to_snake_case(name):
    name = re.sub(r'([a-z\d])([A-Z])', r'\1_\2', name)
    return name.replace("__", "_").lower()


# 生成表名
def get_table_name(prefix, path):
    effective_path = path[1:] if path and path[0] == 'result' else path
    return to_snake_case('_'.join([prefix] + effective_path))


# 生成字段定义
def gen_column(field_name, field_type, remark):
    col_type = TYPE_MAP.get(field_type, "VARCHAR(255)")
    # 从 remark 中移除换行符，避免 SQL 语法错误
    clean_remark = remark.replace('\n', ' ').replace('\r', '') if remark else ''
    return f"  `{to_snake_case(field_name)}` {col_type} COMMENT '{clean_remark}'"


# ### 核心修改点 1: parse_fields 函数 ###
# 增加了 chinese_name 参数，用于生成更友好的表注释
def parse_fields(fields: dict, prefix: str, chinese_name: str, path: list, tables: dict, parent_table=None):
    """
    递归解析字段，生成表结构定义。

    :param fields: 当前层级的字段定义字典
    :param prefix: 表名的英文前缀 (e.g., "base_info")
    :param chinese_name: 表注释的中文名称 (e.g., "工商信息")
    :param path: 当前解析的路径
    :param tables: 用于存储所有表定义的字典
    :param parent_table: 父表名称，用于建立外键关系
    """
    table_name = get_table_name(prefix, path)
    if table_name not in tables:
        # 使用 chinese_name 生成注释
        sub_path_str = '/'.join(path[1:])
        full_comment = f"{chinese_name} - {sub_path_str}" if sub_path_str else chinese_name

        tables[table_name] = {
            "columns": [],
            "comment": full_comment,
            "foreign_key": None if parent_table is None else (parent_table, to_snake_case(f"{parent_table}_id"))
        }

    for key, meta in fields.items():
        field_type = meta.get("type", "String")
        remark = meta.get("remark", "")
        if field_type in ["Object", "Array"] and "_" in meta:
            # 递归调用时，将 chinese_name 传递下去
            parse_fields(meta["_"], prefix, chinese_name, path + [key], tables, table_name)
            continue
        else:
            tables[table_name]["columns"].append(gen_column(key, field_type, remark))


def generate_sql(tables: dict):
    sql_list = []
    for table, data in tables.items():
        lines = [f"CREATE TABLE IF NOT EXISTS `{table}` ("]
        lines.append(f"  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',")

        if data["foreign_key"]:
            fk_table, fk_field = data["foreign_key"]
            lines.append(f"  `{fk_field}` BIGINT COMMENT '外键, 关联 `{fk_table}`.id',")

        lines.extend(data["columns"])

        # 移除最后一个可能存在的逗号
        if lines[-1].strip().endswith(','):
            lines[-1] = lines[-1].rstrip(',')

        lines.append(f") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='{data['comment']}';")
        sql_list.append("\n".join(lines))
    return "\n\n".join(sql_list)


def process_api(api_id):
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
        print(return_param_str, file=sys.stderr)  # 输出到标准错误流，便于调试
        if not return_param_str:
            raise ValueError(f"API ID {api_id} 的响应中未找到 'returnParam' 字段")
        return return_param_str
    except requests.exceptions.RequestException as e:
        print(f"ERROR: 请求API ID {api_id} 时发生网络错误: {e}", file=sys.stderr)
        return None
    except (ValueError, json.JSONDecodeError) as e:
        print(f"ERROR: 处理API ID {api_id} 的数据时发生错误: {e}", file=sys.stderr)
        return None



# --- 此处是所有未发生变化的辅助函数 ---
# 为了简洁，此处省略，请在您的文件中保留它们
# TYPE_MAP = { ... }
# def to_snake_case(...): ...
# def get_table_name(...): ...
# def gen_column(...): ...
# def parse_fields(...): ...
# def generate_sql(...): ...
# def process_api(...): ...
# -----------------------------------------


def main():
    all_sql_statements = []
    for api_id, (root_table, chinese_comment) in INTERFACE_DICT.items():
        print(f"--- 正在处理API: {api_id} ({chinese_comment}) ---")

        return_param_string = process_api(api_id)

        if return_param_string:
            try:
                return_param_dict = json.loads(return_param_string)
                result_node = return_param_dict.get("result", {})
                result_fields = None

                # ### 这是最终的、最完善的解析逻辑 ###
                if result_node and isinstance(result_node, dict):
                    nested_content = result_node.get("_")

                    if nested_content:
                        # 检查 `_` 键的内容类型
                        if isinstance(nested_content, dict):
                            # 情况1: 内容是字典，直接使用 (适配 API 1001)
                            print("  [信息] 检测到 'result._' 字典结构，直接使用。")
                            result_fields = nested_content
                        elif isinstance(nested_content, str):
                            # 情况2: 内容是字符串，需要二次解析
                            print("  [信息] 检测到 'result._' 字符串结构，正在解析...")
                            try:
                                result_fields = json.loads(nested_content)
                            except json.JSONDecodeError as e:
                                print(f"  [错误] 'result._' 字符串无法被解析为JSON: {e}")
                        else:
                            print(f"  [警告] 'result._' 键的内容是无法处理的类型: {type(nested_content)}")
                    else:
                        # 情况3: `result` 键下没有 `_`，则认为 result 本身就是字段定义
                        print("  [信息] 未检测到 'result._'，尝试使用 'result' 直接结构。")
                        result_fields = result_node

                # 如果成功获取到字段定义，则生成SQL
                if result_fields:
                    tables = {}
                    parse_fields(result_fields, root_table, chinese_comment, ["result"], tables)
                    sql = generate_sql(tables)
                    all_sql_statements.append(
                        f"-- ==================================================\n-- SQL for {chinese_comment} (API ID: {api_id})\n-- ==================================================\n{sql}")
                    print(f"  [成功] API {api_id} 的SQL已生成。")
                else:
                    print(f"  [警告] API {api_id} 中未找到有效的字段定义。")
                    print("  [调试信息] 'returnParam' 解析后的内容如下:")
                    print(json.dumps(return_param_dict, indent=2, ensure_ascii=False))

            except json.JSONDecodeError as e:
                print(f"  [错误] API {api_id} 的 'returnParam' 字符串不是有效的JSON: {e}")
        else:
            print(f"  [跳过] 未能从API {api_id} 获取数据。")
        print("-" * 50)

    # ... (后续的汇总和文件写入部分保持不变) ...
    final_sql_output = "\n\n".join(all_sql_statements)
    with open("generated_tables.sql", "w", encoding="utf-8") as f:
        f.write(final_sql_output)

    print("\n\n✅ 所有SQL语句已生成完毕，并保存到文件 `generated_tables.sql`。")



if __name__ == "__main__":
    main()

