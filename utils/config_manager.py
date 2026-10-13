import os
import json
import sys
import tempfile

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG_DIR = 'config'

def get_config_path(filename):
    base = get_base_path()
    return os.path.join(base, CONFIG_DIR, filename)

def load_json_safe(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"加载配置文件失败: {file_path}, 错误: {e}")
        return None

def save_json_safe(file_path, data):
    # 原子写入：先写同目录临时文件再整体替换，避免直接用 'w' 截断时
    # 被并发写/进程中断搞成空文件或半截 JSON（读回时会被当成"没有数据"）
    tmp_path = None
    try:
        directory = os.path.dirname(file_path)
        os.makedirs(directory, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".tmp-", suffix=".json")
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, file_path)
        return True
    except Exception as e:
        print(f"保存配置文件失败: {file_path}, 错误: {e}")
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        return False
