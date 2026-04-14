import json
from utils.config_manager import init_config, get_config_path_by_name, load_json_safe, save_json_safe, get_assets_path

init_config()

rule_config_path = get_config_path_by_name('rule_config.json')
rule_info_path = get_config_path_by_name('rule_info.json')
url_config_path = get_config_path_by_name('url_config.json')
ai_config_path = get_config_path_by_name('ai_config.json')
search_config_path = get_config_path_by_name('search_config.json')

def load_json(file_path):
    data = load_json_safe(file_path)
    if data is None:
        assets_path = file_path.replace('config/', 'assets/')
        data = load_json_safe(assets_path)
        if data is not None:
            save_json_safe(file_path, data)
        else:
            return {}
    return data

def get_url_config():
    url_config = load_json(url_config_path)
    if not url_config:
        url_config = load_json_safe(get_assets_path('url_config.json'))
    
    qb_host = url_config.get('qBittorrent_host')
    qb_port = url_config.get('qBittorrent_port')
    ddp_host = url_config.get('dandanPlay_host')
    ddp_port = url_config.get('dandanPlay_port')
    
    if not qb_host or not qb_port or not ddp_host or not ddp_port:
        return None
    
    return {
        'qBittorrent_BASE_URL': f"http://{qb_host}:{qb_port}/api/v2/",
        'dandanPlay_BASE_URL': f"http://{ddp_host}:{ddp_port}",
        'qBittorrent_host': qb_host,
        'qBittorrent_port': qb_port,
        'qBittorrent_username': url_config.get('qBittorrent_username'),
        'qBittorrent_password': url_config.get('qBittorrent_password'),
        'dandanPlay_host': ddp_host,
        'dandanPlay_port': ddp_port
    }

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
    save_json_safe(file_path, data)

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

# 获取搜索配置
def get_search_config():
    search_config = load_json(search_config_path)
    if not search_config:
        search_config = load_json_safe(get_assets_path('search_config.json'))
    return search_config or {}

# 保存搜索配置
def save_search_config(data):
    default_config = load_json_safe(get_assets_path('search_config.json')) or {}
    search_config = {
        "search_header": data.get("search_header", default_config.get("search_header", "")),
        "proxy_enabled": data.get("proxy_enabled", default_config.get("proxy_enabled", False)),
        "proxy_protocol": data.get("proxy_protocol", default_config.get("proxy_protocol", "http")),
        "proxy_host": data.get("proxy_host", default_config.get("proxy_host", "")),
        "proxy_port": data.get("proxy_port", default_config.get("proxy_port", ""))
    }
    save_json(search_config_path, search_config)
    return True

# 获取URL配置
def get_url_config_all():
    url_config = load_json(url_config_path)
    if not url_config:
        url_config = load_json_safe(get_assets_path('url_config.json'))
    
    if not url_config:
        return None
    
    return {
        "qBittorrent_host": url_config.get("qBittorrent_host"),
        "qBittorrent_port": url_config.get("qBittorrent_port"),
        "qBittorrent_username": url_config.get("qBittorrent_username"),
        "qBittorrent_password": url_config.get("qBittorrent_password"),
        "dandanPlay_host": url_config.get("dandanPlay_host"),
        "dandanPlay_port": url_config.get("dandanPlay_port")
    }

# 保存URL配置
def save_url_config(data):
    default_config = load_json_safe(get_assets_path('url_config.json')) or {}
    url_config = {
        "qBittorrent_host": data.get("qBittorrent_host", default_config.get("qBittorrent_host")),
        "qBittorrent_port": data.get("qBittorrent_port", default_config.get("qBittorrent_port")),
        "qBittorrent_username": data.get("qBittorrent_username", default_config.get("qBittorrent_username")),
        "qBittorrent_password": data.get("qBittorrent_password", default_config.get("qBittorrent_password")),
        "dandanPlay_host": data.get("dandanPlay_host", default_config.get("dandanPlay_host")),
        "dandanPlay_port": data.get("dandanPlay_port", default_config.get("dandanPlay_port"))
    }
    save_json(url_config_path, url_config)
    return True