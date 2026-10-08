# 日志初始化与归档：实时输出到控制台和 logs/backend.log，关闭时归档到 logs/archive/
import logging
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime

from utils.config_manager import get_base_path, get_config_path

logger = logging.getLogger(__name__)

LOG_DIR_NAME = "logs"
LIVE_LOG_NAME = "backend.log"
ARCHIVE_DIR_NAME = "archive"

_live_log_file = None
_archived = False


def _log_dir():
    path = os.path.join(get_base_path(), LOG_DIR_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def _archive_file(src):
    """把日志文件移到 logs/archive/backend_时间戳.log，返回归档路径"""
    archive_dir = os.path.join(os.path.dirname(src), ARCHIVE_DIR_NAME)
    os.makedirs(archive_dir, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = os.path.join(archive_dir, f"backend_{stamp}.log")
    index = 1
    while os.path.exists(target):
        target = os.path.join(archive_dir, f"backend_{stamp}_{index}.log")
        index += 1

    os.replace(src, target)
    return target


def setup_logging():
    """初始化日志：控制台实时输出 + 写入 logs/backend.log

    若上次异常退出残留了日志文件，先归档，保证本次运行是全新日志。
    """
    global _live_log_file
    live_file = os.path.join(_log_dir(), LIVE_LOG_NAME)

    if os.path.isfile(live_file) and os.path.getsize(live_file) > 0:
        try:
            _archive_file(live_file)
        except OSError as e:
            print(f"[log] 残留日志归档失败: {e}")

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for handler in list(root.handlers):
        root.removeHandler(handler)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    file_handler = logging.FileHandler(live_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    _live_log_file = live_file
    return live_file


def archive_log():
    """关闭时归档实时日志（幂等，可安全重复调用）"""
    global _archived, _live_log_file
    if _archived or not _live_log_file or not os.path.isfile(_live_log_file):
        return
    _archived = True

    # 先关闭文件句柄，否则 Windows 上无法重命名
    root = logging.getLogger()
    for handler in list(root.handlers):
        if isinstance(handler, logging.FileHandler):
            handler.close()
            root.removeHandler(handler)

    try:
        if os.path.getsize(_live_log_file) == 0:
            os.remove(_live_log_file)
            return
        target = _archive_file(_live_log_file)
        print(f"[log] 日志已归档: {target}")
    except OSError as e:
        print(f"[log] 日志归档失败: {e}")


def _command_version(command):
    """返回命令的首行版本信息，不可用返回 None"""
    try:
        result = subprocess.run(
            [command, "-version"],
            capture_output=True,
            stdin=subprocess.DEVNULL,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    lines = result.stdout.decode("utf-8", "ignore").splitlines()
    return lines[0].strip() if lines else "未知"


def log_startup_info():
    """启动自检：打印本机环境与后端关键状态，便于排查环境问题"""
    from utils.fun_config import get_url_config

    base = get_base_path()
    frozen = getattr(sys, "frozen", False)

    lines = [
        "==================== 启动自检 ====================",
        f"启动时间   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"运行方式   : {'打包程序' if frozen else '源码'}",
        f"基础目录   : {base}",
        f"工作目录   : {os.getcwd()}",
        f"Python     : {platform.python_version()} ({platform.architecture()[0]})",
        f"操作系统   : {platform.platform()}",
        f"CPU 核心   : {os.cpu_count()}",
    ]

    ffmpeg = _command_version("ffmpeg")
    ffprobe = _command_version("ffprobe")
    lines.append(f"ffmpeg     : {shutil.which('ffmpeg') or '未找到'}")
    lines.append(f"             {ffmpeg or '不可用（未安装或不在 PATH）'}")
    lines.append(f"ffprobe    : {shutil.which('ffprobe') or '未找到'}")
    lines.append(f"             {ffprobe or '不可用（未安装或不在 PATH）'}")

    config_dir = os.path.dirname(get_config_path("x"))
    lines.append(f"配置目录   : {config_dir}")
    try:
        files = sorted(f for f in os.listdir(config_dir) if f.endswith(".json"))
        lines.append(f"配置文件   : {', '.join(files) if files else '无'}")
    except OSError:
        lines.append("配置文件   : 目录不可读")

    try:
        url_config = get_url_config()
        lines.append(f"dandanPlay : {url_config.get('dandanPlay_BASE_URL')}")
        lines.append(f"qBittorrent: {url_config.get('qBittorrent_BASE_URL')}")
    except Exception as e:
        lines.append(f"URL 配置   : 读取失败（{e}）")

    lines.append(f"日志文件   : {_live_log_file or '-'}")
    lines.append(f"缓存目录   : {os.path.join(base, 'cache')}")
    lines.append("=================================================")

    for line in lines:
        logger.info(line)
