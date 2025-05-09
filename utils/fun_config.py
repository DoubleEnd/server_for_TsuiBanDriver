import json

rule_config_path = 'assets/rule_config.json'
rule_info_path = 'assets/rule_info.json'
url_config_path = 'assets/url_config.json'
ai_config_path = 'assets/ai_config.json'

# 读取规则配置文件
def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def get_url_config():
    url_config = load_json(url_config_path)
    return url_config

# 获取规则配置文件
def get_rule_config():
    rule_config = load_json(rule_config_path)
    return rule_config

# 获取规则信息文件
def get_rule_info():
    rule_info = load_json(rule_info_path)
    return rule_info

# 保存规则配置文件
def save_json(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

# 更新使用的规则
def update_used_rule(rule_name):
    rule_config = load_json(rule_config_path)

    is_have = False
    for rule in rule_config['rule_list']:
        if rule['name'] == rule_name:
            rule_config['used_rule'] = rule
            save_json(rule_config_path, rule_config)
            is_have =  True
            break
    return is_have

#返回错误信息
def request_rule_msg(rule_name):
    rule_info_data = load_json(rule_info_path)
    rule_info = rule_info_data.get(rule_name)  # 获取选择的规则信息
    if rule_info:
        return f"使用规则：{rule_name}\n{rule_info}"
    else:
        return f"未配置规则：{rule_name}"

# 匹配规则
def match_rule():
    rule_config = load_json(rule_config_path)
    used_rule_name = rule_config["used_rule"]["name"]
    rule_info = load_json(rule_info_path)
    return rule_info.get(used_rule_name)

# 新增或编辑规则
def add_edit_rule(data):
    rule_config = load_json(rule_config_path)
    rule_info = load_json(rule_info_path)

    # 检查规则是否已存在
    is_exist = False
    for rule in rule_config['rule_list']:
        if rule['name'] == data["name"]:
            # 如果规则已存在，更新规则信息
            rule['title'] = data["title"]
            rule_info[data["name"]] = data["info"]  # 更新 rule_info 中的信息
            is_exist = True
            break

    # 如果规则不存在，新增规则
    if not is_exist:
        new_rule = {
            'name': data["name"],
            'title': data["title"],
        }
        rule_config['rule_list'].append(new_rule)
        rule_info[data["name"]] = data["info"]  # 新增 rule_info 中的信息

    # 保存更新后的配置文件
    save_json(rule_config_path, rule_config)
    save_json(rule_info_path, rule_info)

    return is_exist

# 删除规则
def delete_rule(rule_name):
    rule_config = load_json(rule_config_path)
    rule_info = load_json(rule_info_path)

    # 检查规则是否已存在
    is_exist = False
    for rule in rule_config['rule_list']:
        if rule['name'] == rule_name:
            # 如果规则已存在，从 rule_list 中删除该规则
            rule_config['rule_list'].remove(rule)
            is_exist = True
            break

    # 如果规则存在，从 rule_info 中删除该规则的信息
    if is_exist:
        rule_info.pop(rule_name, None)  # 使用 pop 方法删除键，避免 KeyError

    # 保存更新后的配置文件
    save_json(rule_config_path, rule_config)
    save_json(rule_info_path, rule_info)

    return is_exist

# 新增或修改 AI 配置
def add_edit_ai_config(data):
    ai_config = load_json(ai_config_path)
    key = data.get("ai_config_key")
    value = data.get("ai_config_value")
    if key and value:
        ai_config[key] = value
        save_json(ai_config_path, ai_config)
        return True
    return False

# 删除 AI 配置
def delete_ai_config(key):
    ai_config = load_json(ai_config_path)
    if key in ai_config:
        del ai_config[key]
        save_json(ai_config_path, ai_config)
        return True
    return False