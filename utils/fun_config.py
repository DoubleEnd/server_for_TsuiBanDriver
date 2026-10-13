import copy
import hashlib
import json
import os
from utils._version import VERSION
from utils.config_manager import get_config_path, load_json_safe, save_json_safe

rule_config_path = get_config_path('rule_config.json')
rule_info_path = get_config_path('rule_info.json')
url_config_path = get_config_path('url_config.json')
ai_chat_config_path = get_config_path('ai_chat_config.json')
search_config_path = get_config_path('search_config.json')
scan_config_path = get_config_path('scan_config.json')
auth_config_path = get_config_path('auth_config.json')

DEFAULT_URL_CONFIG = {
    "qBittorrent_host": "127.0.0.1",
    "qBittorrent_port": 8080,
    "qBittorrent_username": "",
    "qBittorrent_password": "",
    # 是否绑定 qBittorrent：未绑定时前端不展示订阅/下载相关功能，后端也可正常运行
    "qBittorrent_enabled": False,
    # 弹弹play 开放 API 凭证（签名模式）：用于文件识别与番剧信息
    "dandanPlay_app_id": "",
    "dandanPlay_app_secret": ""
}

# 媒体库扫描配置：扫描目录列表 + 黑名单（路径或文件名的正则，命中即跳过）
DEFAULT_SCAN_CONFIG = {
    "scan_paths": [],
    "scan_blacklist": [],
    # 周期自动扫描：默认开启，每 30 分钟触发一次快速扫描（只处理从未扫描过的新文件）
    "auto_scan_enabled": True,
    "auto_scan_interval": 30
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

DEFAULT_AI_CHAT_CONFIG = {
    "api_key": "",
    "base_url": "https://api.deepseek.com",
    "model": "deepseek-v4-flash",
    "max_tool_rounds": 50
}

DEFAULT_AUTH_CONFIG = {
    "auth_enabled": False,
    "auth_password": "admin123"
}

# 生成访问令牌用的固定盐值，修改密码后旧令牌自动失效
_AUTH_TOKEN_SALT = "tsuiban_driver_auth"

# 应用信息内置在代码中，不再落地为外部配置文件，由 /allVersion 接口直接返回
APP_INFO = [
    { "name": "后端版本", "value": VERSION },
    { "name": "作者", "value": "@DoubleEnd", "href": "https://github.com/DoubleEnd"},
    { "name": "邮箱", "value": "doubleend@qq.com" },
    { "name": "项目地址", "value": "server_for_TsuiBanDriver", "href": "https://github.com/DoubleEnd/server_for_TsuiBanDriver" },
    { "name": "开源协议", "value": "CC BY-NC 4.0", "href": "https://creativecommons.org/licenses/by-nc/4.0/deed.zh-hans" },
    { "name": "qbittorrent版本", "value": "", "href":"https://www.fosshub.com/qBittorrent.html"},
    { "name": "qbittorrentWebApi版本", "value": "", "href":"https://github.com/qbittorrent/wiki/blob/master/WebUI-API-(qBittorrent-5.0).md"}
]

def ensure_config_file(file_path, default_config):
    if not os.path.exists(file_path):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)

ensure_config_file(url_config_path, DEFAULT_URL_CONFIG)
ensure_config_file(search_config_path, DEFAULT_SEARCH_CONFIG)
ensure_config_file(scan_config_path, DEFAULT_SCAN_CONFIG)
ensure_config_file(rule_config_path, DEFAULT_RULE_CONFIG)
ensure_config_file(rule_info_path, {})
ensure_config_file(ai_chat_config_path, DEFAULT_AI_CHAT_CONFIG)
ensure_config_file(auth_config_path, DEFAULT_AUTH_CONFIG)

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
        'qBittorrent_host': url_config['qBittorrent_host'],
        'qBittorrent_port': url_config['qBittorrent_port'],
        'qBittorrent_username': url_config.get('qBittorrent_username'),
        'qBittorrent_password': url_config.get('qBittorrent_password'),
        'dandanPlay_app_id': url_config.get('dandanPlay_app_id', ''),
        'dandanPlay_app_secret': url_config.get('dandanPlay_app_secret', '')
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

def get_ai_chat_config():
    """获取 AI 对话配置，缺失字段自动用默认值补全"""
    config = load_json(ai_chat_config_path)
    if not config:
        config = {}
    changed = False
    for key, default_value in DEFAULT_AI_CHAT_CONFIG.items():
        if key not in config:
            config[key] = default_value
            changed = True
    if changed:
        save_json_safe(ai_chat_config_path, config)
    return config

def save_ai_chat_config(data):
    """保存 AI 对话配置，未提供的字段保持原值"""
    config = get_ai_chat_config()
    for key in ("api_key", "base_url", "model"):
        if key in data:
            config[key] = data[key]
    if data.get("max_tool_rounds") is not None:
        config["max_tool_rounds"] = int(data["max_tool_rounds"])
    save_json_safe(ai_chat_config_path, config)
    return True

def get_search_config():
    return load_json(search_config_path) or DEFAULT_SEARCH_CONFIG

def get_app_info():
    # 返回副本，避免调用方（如 /allVersion 回填 qBittorrent 版本）污染内置数据
    return copy.deepcopy(APP_INFO)

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
        "qBittorrent_enabled": bool(url_config.get("qBittorrent_enabled", False)),
        "dandanPlay_app_id": url_config.get("dandanPlay_app_id", ""),
        # 密钥不下发给前端，只告知是否已配置
        "dandanPlay_has_secret": bool(url_config.get("dandanPlay_app_secret", ""))
    }

def save_url_config(data):
    """保存 URL/凭证配置：未传入的字段保留原值，避免只改一项时其他项被重置"""
    existing = load_json(url_config_path) or {}

    def pick(key):
        if key in data:
            return data[key]
        return existing.get(key, DEFAULT_URL_CONFIG.get(key))

    url_config = {
        "qBittorrent_host": pick("qBittorrent_host"),
        "qBittorrent_port": pick("qBittorrent_port"),
        "qBittorrent_username": pick("qBittorrent_username"),
        "qBittorrent_password": pick("qBittorrent_password"),
        "qBittorrent_enabled": bool(pick("qBittorrent_enabled")),
        "dandanPlay_app_id": str(pick("dandanPlay_app_id") or ""),
        "dandanPlay_app_secret": str(pick("dandanPlay_app_secret") or "")
    }
    save_json_safe(url_config_path, url_config)
    return True

def get_scan_config():
    """获取扫描配置，缺失字段自动用默认值补全"""
    config = load_json(scan_config_path)
    if not config:
        config = {}
    changed = False
    for key, default_value in DEFAULT_SCAN_CONFIG.items():
        if key not in config:
            config[key] = default_value
            changed = True
    if changed:
        save_json_safe(scan_config_path, config)
    return config

def save_scan_config(data):
    """保存扫描配置：扫描目录、黑名单与周期自动扫描设置

    扫描目录/黑名单做去空去重；未提交的字段沿用已保存的值
    （前端各入口只提交自己负责的字段）。
    """
    def _clean(values):
        result = []
        for item in values or []:
            text = str(item).strip()
            if text and text not in result:
                result.append(text)
        return result

    current = get_scan_config()

    enabled = data.get("auto_scan_enabled", current.get("auto_scan_enabled"))
    if isinstance(enabled, str):
        enabled = enabled.strip().lower() in ("1", "true", "yes", "on")

    try:
        interval = max(1, int(data.get("auto_scan_interval", current.get("auto_scan_interval"))))
    except (TypeError, ValueError):
        interval = DEFAULT_SCAN_CONFIG["auto_scan_interval"]

    config = {
        "scan_paths": _clean(data.get("scan_paths", current.get("scan_paths"))),
        "scan_blacklist": _clean(data.get("scan_blacklist", current.get("scan_blacklist"))),
        "auto_scan_enabled": bool(enabled),
        "auto_scan_interval": interval
    }
    save_json_safe(scan_config_path, config)
    return True

def get_auth_config():
    """获取密码保护配置，缺失字段自动用默认值补全"""
    config = load_json(auth_config_path)
    if not config:
        config = {}
    changed = False
    for key, default_value in DEFAULT_AUTH_CONFIG.items():
        if key not in config:
            config[key] = default_value
            changed = True
    if changed:
        save_json_safe(auth_config_path, config)
    return config

def save_auth_config(data):
    """保存密码保护配置，密码留空表示不修改"""
    config = get_auth_config()
    if "auth_enabled" in data:
        config["auth_enabled"] = bool(data["auth_enabled"])
    if data.get("auth_password"):
        config["auth_password"] = str(data["auth_password"])
    save_json_safe(auth_config_path, config)
    return True

def get_auth_token():
    """由当前密码推导访问令牌"""
    password = get_auth_config()["auth_password"]
    return hashlib.sha256(f"{password}{_AUTH_TOKEN_SALT}".encode('utf-8')).hexdigest()

def check_auth_token(token):
    """校验访问令牌，未开启密码保护时直接放行"""
    if not get_auth_config()["auth_enabled"]:
        return True
    if not token:
        return False
    return token == get_auth_token()

