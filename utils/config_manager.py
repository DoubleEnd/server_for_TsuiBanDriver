import os
import json
import shutil

CONFIG_DIR = 'config'
ASSETS_DIR = 'assets'

CONFIG_FILES = [
    'ai_config.json',
    'url_config.json',
    'search_config.json',
    'rule_config.json',
    'rule_info.json'
]

def get_config_path(filename):
    return os.path.join(CONFIG_DIR, filename)

def get_assets_path(filename):
    return os.path.join(ASSETS_DIR, filename)

def load_json_safe(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"加载配置文件失败: {file_path}, 错误: {e}")
        return None

def save_json_safe(file_path, data):
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存配置文件失败: {file_path}, 错误: {e}")
        return False

def init_config():
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)

    for filename in CONFIG_FILES:
        config_path = get_config_path(filename)
        assets_path = get_assets_path(filename)

        if os.path.exists(config_path):
            data = load_json_safe(config_path)
            if data is not None:
                continue

        if os.path.exists(assets_path):
            data = load_json_safe(assets_path)
            if data is not None:
                save_json_safe(config_path, data)
            else:
                print(f"警告: assets/{filename} 格式错误，使用空配置")
                save_json_safe(config_path, {})
        else:
            print(f"警告: assets/{filename} 不存在，创建空配置")
            save_json_safe(config_path, {})

def get_config_path_by_name(filename):
    config_path = get_config_path(filename)
    if os.path.exists(config_path):
        data = load_json_safe(config_path)
        if data is not None:
            return config_path
    
    assets_path = get_assets_path(filename)
    if os.path.exists(assets_path):
        data = load_json_safe(assets_path)
        if data is not None:
            save_json_safe(config_path, data)
            return config_path
    
    return assets_path