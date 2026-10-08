# 本地视频封面 / 进度条预览缩略图生成（依赖 ffmpeg、ffprobe）
import hashlib
import json
import logging
import math
import os
import subprocess

from utils.config_manager import get_base_path

logger = logging.getLogger(__name__)

# 生成图片的缓存目录（项目根目录下 cache/thumbnails）
_CACHE_DIR_NAME = os.path.join("cache", "thumbnails")

# 封面参数
_POSTER_WIDTH = 640
_POSTER_SEEK_RATIO = 0.1

# 进度条预览精灵图参数
_SPRITE_NUMBER = 100
_SPRITE_COLUMN = 10
_SPRITE_FRAME_WIDTH = 160

_FFMPEG_TIMEOUT = 600


def _get_cache_dir():
    cache_dir = os.path.join(get_base_path(), _CACHE_DIR_NAME)
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def _cache_key(file_path):
    """按 路径 + 修改时间 + 大小 生成缓存键，源文件变更后自动失效"""
    stat = os.stat(file_path)
    raw = f"{file_path}|{stat.st_mtime_ns}|{stat.st_size}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _cache_path(file_path, suffix):
    return os.path.join(_get_cache_dir(), f"{_cache_key(file_path)}_{suffix}.jpg")


def _run_ffmpeg(args):
    """执行 ffmpeg，成功返回 True"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args],
            capture_output=True,
            timeout=_FFMPEG_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError) as e:
        logger.error(f"[thumbnail] ffmpeg 执行失败: {e}")
        return False

    if result.returncode != 0:
        logger.error(f"[thumbnail] ffmpeg 返回错误: {result.stderr.decode('utf-8', 'ignore')}")
        return False
    return True


def probe_video(file_path):
    """用 ffprobe 获取视频的宽、高、时长（秒）；失败返回 None"""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height:format=duration",
                "-of", "json", file_path,
            ],
            capture_output=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as e:
        logger.error(f"[thumbnail] ffprobe 执行失败: {e}")
        return None

    if result.returncode != 0:
        logger.error(f"[thumbnail] ffprobe 返回错误: {result.stderr.decode('utf-8', 'ignore')}")
        return None

    try:
        data = json.loads(result.stdout.decode("utf-8", "ignore"))
        stream = (data.get("streams") or [{}])[0]
        duration = float(data.get("format", {}).get("duration") or 0)
        return {
            "width": int(stream.get("width") or 0),
            "height": int(stream.get("height") or 0),
            "duration": duration,
        }
    except (ValueError, json.JSONDecodeError, IndexError, TypeError) as e:
        logger.error(f"[thumbnail] 解析 ffprobe 结果失败: {e}")
        return None


def get_poster(file_path):
    """获取视频封面图，返回本地缓存文件路径；失败返回 None"""
    cache_file = _cache_path(file_path, "poster")
    if os.path.isfile(cache_file):
        return cache_file

    info = probe_video(file_path)
    if not info:
        return None

    seek = info["duration"] * _POSTER_SEEK_RATIO
    ok = _run_ffmpeg([
        "-ss", f"{seek:.3f}",
        "-i", file_path,
        "-frames:v", "1",
        "-vf", f"scale={_POSTER_WIDTH}:-2",
        "-q:v", "3",
        cache_file,
    ])
    if not ok or not os.path.isfile(cache_file):
        return None
    return cache_file


def get_sprite_info(file_path):
    """计算进度条预览精灵图的布局信息，前端用于配置 Artplayer thumbnails"""
    info = probe_video(file_path)
    if not info or not info["duration"] or not info["width"] or not info["height"]:
        return None

    number = _SPRITE_NUMBER
    column = _SPRITE_COLUMN
    rows = math.ceil(number / column)
    # 保持视频宽高比，高度取偶数（编码要求）
    height = int(round(_SPRITE_FRAME_WIDTH * info["height"] / info["width"] / 2)) * 2

    return {
        "number": number,
        "column": column,
        "rows": rows,
        "width": _SPRITE_FRAME_WIDTH,
        "height": max(height, 2),
        "fps": number / info["duration"],
        "duration": info["duration"],
    }


def get_sprite(file_path):
    """获取进度条预览精灵图，返回本地缓存文件路径；失败返回 None"""
    cache_file = _cache_path(file_path, "sprite")
    if os.path.isfile(cache_file):
        return cache_file

    info = get_sprite_info(file_path)
    if not info:
        return None

    filter_expr = (
        f"fps={info['fps']:.6f},"
        f"scale={info['width']}:{info['height']},"
        f"tile={info['column']}x{info['rows']}"
    )
    # 长视频只解码关键帧，否则为抽 100 帧要解码整部视频（电影级别需数十分钟）。
    # 短视频关键帧太少会导致预览图大片空白，此时仍走完整解码（时长本身也不长）。
    args = []
    if info["duration"] >= info["number"] * 10:
        args += ["-skip_frame", "nokey"]
    args += [
        "-i", file_path,
        "-vf", filter_expr,
        "-frames:v", "1",
        "-q:v", "5",
        cache_file,
    ]
    ok = _run_ffmpeg(args)
    if not ok or not os.path.isfile(cache_file):
        return None
    return cache_file
