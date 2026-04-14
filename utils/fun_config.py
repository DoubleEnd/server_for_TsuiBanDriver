import json
import os
from utils.config_manager import get_config_path, load_json_safe, save_json_safe

rule_config_path = get_config_path('rule_config.json')
rule_info_path = get_config_path('rule_info.json')
url_config_path = get_config_path('url_config.json')
ai_config_path = get_config_path('ai_config.json')
search_config_path = get_config_path('search_config.json')
app_info_path = get_config_path('app_info.json')

DEFAULT_URL_CONFIG = {
    "qBittorrent_host": "127.0.0.1",
    "qBittorrent_port": 8080,
    "qBittorrent_username": "admin",
    "qBittorrent_password": "123456",
    "dandanPlay_host": "127.0.0.1",
    "dandanPlay_port": 8888
}

DEFAULT_SEARCH_CONFIG = {
    "search_header": "",
    "proxy_enabled": False,
    "proxy_protocol": "http",
    "proxy_host": "",
    "proxy_port": ""
}

DEFAULT_RULE_CONFIG = {
    "used_rule": {
        "name": "",
        "title": ""
    },
    "rule_list": []
}

DEFAULT_AI_CONFIG = {
    "valid_models": ["tiny", "small", "medium"],
    "valid_devices": ["cpu", "gpu"],
    "default_model": "tiny",
    "default_device": "cpu"
}

DEFAULT_APP_INFO = [
    { "name": "后端版本", "value": "1.0.0" },
    { "name": "作者", "value": "@DoubleEnd", "href": "https://github.com/DoubleEnd"},
    { "name": "邮箱", "value": "doubleend@qq.com" },
    { "name": "项目地址", "value": "server_for_TsuiBanDriver", "href": "https://github.com/DoubleEnd/server_for_TsuiBanDriver" },
    { "name": "开源协议", "value": "CC BY-NC 4.0", "href": "https://creativecommons.org/licenses/by-nc/4.0/deed.zh-hans" },
    { "name": "分割线" },
    { "name": "qbittorrent版本", "value": "", "href":"https://www.fosshub.com/qBittorrent.html"},
    { "name": "qbittorrentWebApi版本", "value": "", "href":"https://github.com/qbittorrent/wiki/blob/master/WebUI-API-(qBittorrent-5.0).md"},
    { "name": "dandanPlay版本", "value": "", "href": "https://www.dandanplay.com/"}
]

def ensure_config_file(file_path, default_config):
    if not os.path.exists(file_path):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)

ensure_config_file(url_config_path, DEFAULT_URL_CONFIG)
ensure_config_file(search_config_path, DEFAULT_SEARCH_CONFIG)
ensure_config_file(rule_config_path, DEFAULT_RULE_CONFIG)
ensure_config_file(rule_info_path, {})
ensure_config_file(ai_config_path, DEFAULT_AI_CONFIG)
ensure_config_file(app_info_path, DEFAULT_APP_INFO)

def load_json(file_path):
    data = load_json_safe(file_path)
    if data is None:
        return {}
    return data

def get_url_config():
    url_config = load_json(url_config_path)
    if not url_config:
        url_config = DEFAULT_URL_CONFIG

    return {
        'qBittorrent_BASE_URL': f"http://{url_config['qBittorrent_host']}:{url_config['qBittorrent_port']}/api/v2/",
        'dandanPlay_BASE_URL': f"http://{url_config['dandanPlay_host']}:{url_config['dandanPlay_port']}",
        'qBittorrent_host': url_config['qBittorrent_host'],
        'qBittorrent_port': url_config['qBittorrent_port'],
        'qBittorrent_username': url_config.get('qBittorrent_username'),
        'qBittorrent_password': url_config.get('qBittorrent_password'),
        'dandanPlay_host': url_config['dandanPlay_host'],
        'dandanPlay_port': url_config['dandanPlay_port']
    }

def get_rule_config():
    return load_json(rule_config_path)

def get_rule_info():
    return load_json(rule_info_path)

def update_used_rule(rule_name):
    rule_config = load_json(rule_config_path)
    is_have = False
    for rule in rule_config['rule_list']:
        if rule['name'] == rule_name:
            rule_config['used_rule'] = rule
            save_json_safe(rule_config_path, rule_config)
            is_have = True
            break
    return is_have

def request_rule_msg(rule_name):
    rule_info_data = load_json(rule_info_path)
    rule_info = rule_info_data.get(rule_name)
    if rule_info:
        return f"使用规则：{rule_name}\n{rule_info}"
    else:
        return f"未配置规则：{rule_name}"

def match_rule():
    rule_config = load_json(rule_config_path)
    used_rule_name = rule_config["used_rule"]["name"]
    rule_info = load_json(rule_info_path)
    return rule_info.get(used_rule_name)

def add_edit_rule(data):
    rule_config = load_json(rule_config_path)
    rule_info = load_json(rule_info_path)
    is_exist = False
    for rule in rule_config['rule_list']:
        if rule['name'] == data["name"]:
            rule['title'] = data["title"]
            rule_info[data["name"]] = data["info"]
            is_exist = True
            break
    if not is_exist:
        new_rule = {
            'name': data["name"],
            'title': data["title"],
        }
        rule_config['rule_list'].append(new_rule)
        rule_info[data["name"]] = data["info"]
    save_json_safe(rule_config_path, rule_config)
    save_json_safe(rule_info_path, rule_info)
    return is_exist

def delete_rule(rule_name):
    rule_config = load_json(rule_config_path)
    rule_info = load_json(rule_info_path)
    is_exist = False
    for rule in rule_config['rule_list']:
        if rule['name'] == rule_name:
            rule_config['rule_list'].remove(rule)
            is_exist = True
            break
    if is_exist:
        rule_info.pop(rule_name, None)
    save_json_safe(rule_config_path, rule_config)
    save_json_safe(rule_info_path, rule_info)
    return is_exist

def add_edit_ai_config(data):
    ai_config = load_json(ai_config_path)
    key = data.get("ai_config_key")
    value = data.get("ai_config_value")
    if key and value:
        ai_config[key] = value
        save_json_safe(ai_config_path, ai_config)
        return True
    return False

def delete_ai_config(key):
    ai_config = load_json(ai_config_path)
    if key in ai_config:
        del ai_config[key]
        save_json_safe(ai_config_path, ai_config)
        return True
    return False

def get_search_config():
    return load_json(search_config_path) or DEFAULT_SEARCH_CONFIG

def get_app_info():
    app_info = load_json(app_info_path)
    if not app_info:
        app_info = DEFAULT_APP_INFO
    return app_info

def save_search_config(data):
    search_config = {
        "search_header": data.get("search_header", DEFAULT_SEARCH_CONFIG["search_header"]),
        "proxy_enabled": data.get("proxy_enabled", DEFAULT_SEARCH_CONFIG["proxy_enabled"]),
        "proxy_protocol": data.get("proxy_protocol", DEFAULT_SEARCH_CONFIG["proxy_protocol"]),
        "proxy_host": data.get("proxy_host", DEFAULT_SEARCH_CONFIG["proxy_host"]),
        "proxy_port": data.get("proxy_port", DEFAULT_SEARCH_CONFIG["proxy_port"])
    }
    save_json_safe(search_config_path, search_config)
    return True

def get_url_config_all():
    url_config = load_json(url_config_path)
    if not url_config:
        url_config = DEFAULT_URL_CONFIG
    return {
        "qBittorrent_host": url_config.get("qBittorrent_host"),
        "qBittorrent_port": url_config.get("qBittorrent_port"),
        "qBittorrent_username": url_config.get("qBittorrent_username"),
        "qBittorrent_password": url_config.get("qBittorrent_password"),
        "dandanPlay_host": url_config.get("dandanPlay_host"),
        "dandanPlay_port": url_config.get("dandanPlay_port")
    }

def save_url_config(data):
    url_config = {
        "qBittorrent_host": data.get("qBittorrent_host", DEFAULT_URL_CONFIG["qBittorrent_host"]),
        "qBittorrent_port": data.get("qBittorrent_port", DEFAULT_URL_CONFIG["qBittorrent_port"]),
        "qBittorrent_username": data.get("qBittorrent_username", DEFAULT_URL_CONFIG["qBittorrent_username"]),
        "qBittorrent_password": data.get("qBittorrent_password", DEFAULT_URL_CONFIG["qBittorrent_password"]),
        "dandanPlay_host": data.get("dandanPlay_host", DEFAULT_URL_CONFIG["dandanPlay_host"]),
        "dandanPlay_port": data.get("dandanPlay_port", DEFAULT_URL_CONFIG["dandanPlay_port"])
    }
    save_json_safe(url_config_path, url_config)
    return True
