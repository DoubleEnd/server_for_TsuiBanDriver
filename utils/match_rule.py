import json

rule_config_path = 'assets/rule_config.json'
rule_info_path = 'assets/rule_info.json'

# 读取规则配置文件
def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

# 获取规则列表名
def get_rule_names():
    config_data = load_json(rule_config_path)
    return config_data

# 保存规则配置文件
def save_json(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

# 更新使用的规则
def update_used_rule(rule_name):
    config_data = load_json(rule_config_path)
    print(rule_name)
    is_have = False
    for rule in config_data['rule_list']:
        if rule['name'] == rule_name:
            config_data['used_rule'] = rule
            save_json(rule_config_path, config_data)
            is_have =  True
            break
    return is_have

# 匹配规则
def request_rule_msg(rule_name):
    rule_info_data = load_json(rule_info_path)
    rule_info = rule_info_data.get(rule_name)  # 获取选择的规则信息
    if rule_info:
        return f"使用规则：{rule_name}\n{rule_info}"
    else:
        return f"未配置规则：{rule_name}"

def match_rule():
    rule_config = load_json(rule_config_path)
    used_rule_name = rule_config["used_rule"]["name"]
    rule_info = load_json(rule_info_path)
    return rule_info.get(used_rule_name)
