# 本地字幕：同目录外挂字幕扫描 + 视频内封文本字幕流提取
import codecs
import hashlib
import json
import logging
import os
import re
import subprocess
import threading
import time

from utils.config_manager import get_base_path

logger = logging.getLogger(__name__)

# 外挂字幕扩展名（仅文本字幕，不含 VobSub 等图形字幕）
_EXTERNAL_EXTS = (".ass", ".ssa", ".srt", ".vtt")

# 外挂字体扩展名：字幕组常随片附带字体，ASS 依赖这些字体才能正确排版
_EXTERNAL_FONT_EXTS = (".ttf", ".otf", ".ttc", ".otc", ".woff", ".woff2")

# 外挂字体常见的子目录名（在视频同目录下查找）
_FONT_SUBDIRS = ("fonts", "font", "字体")

# 可提取为文本的内封字幕编码，图形字幕（PGS/VobSub）不在其中
_TEXT_SUB_CODECS = {"ass", "ssa", "subrip", "srt", "mov_text", "webvtt", "text", "microdvd"}

# 内封字幕提取结果的缓存目录（项目根目录下 cache/subtitles）
_CACHE_DIR_NAME = os.path.join("cache", "subtitles")

# 提取内封字幕需要扫描整个文件，串行执行以避免多请求并发抢占磁盘
_extract_lock = threading.Lock()

# 正在后台预热的视频，避免同一视频重复启动
_prefetching = set()
_prefetch_lock = threading.Lock()

_FFMPEG_TIMEOUT = 300


def _guess_utf16_encoding(data):
    """按 NUL 字节分布猜测无 BOM 的 UTF-16 字节序，非 UTF-16 返回 None

    UTF-16 文本中 ASCII 字符会与 0x00 交错，NUL 占比明显偏高；而用 utf-8 解码
    这类数据不会报错（0x00 是合法 UTF-8 字符），会得到夹带 NUL 的乱码，因此必须
    在 utf-8 之前先做识别。
    """
    sample = data[:4096]
    if len(sample) < 4:
        return None
    if sample.count(0) / len(sample) < 0.15:
        return None
    even_zeros = sample[0::2].count(0)
    odd_zeros = sample[1::2].count(0)
    if even_zeros > odd_zeros * 2:
        return "utf-16-be"
    if odd_zeros > even_zeros * 2:
        return "utf-16-le"
    return None


def _decode_bytes(data):
    """按常见字幕编码解码为 UTF-8 文本"""
    if not data:
        return ""
    # 带 BOM：utf-16 会自动识别 LE/BE 并去掉 BOM
    if data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return data.decode("utf-16")
    if data.startswith(codecs.BOM_UTF8):
        return data.decode("utf-8-sig")
    # 无 BOM 的 UTF-16 需要先于 utf-8 判断
    guessed = _guess_utf16_encoding(data)
    if guessed:
        try:
            return data.decode(guessed)
        except UnicodeDecodeError:
            pass
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "big5"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", "ignore")


def list_external_subtitles(video_path):
    """扫描视频同目录下的外挂字幕（文件名模糊包含视频名，忽略大小写）"""
    directory = os.path.dirname(video_path)
    video_stem = os.path.splitext(os.path.basename(video_path))[0].lower()
    subtitles = []
    try:
        names = os.listdir(directory)
    except OSError as e:
        logger.error(f"[subtitle] 读取视频目录失败: {e}")
        return subtitles

    for name in sorted(names):
        stem, ext = os.path.splitext(name)
        if ext.lower() not in _EXTERNAL_EXTS:
            continue
        if video_stem not in stem.lower():
            continue
        subtitles.append({
            "source": "external",
            "name": name,
            "path": os.path.join(directory, name),
        })
    return subtitles


def list_internal_subtitles(video_path):
    """用 ffprobe 读取视频内封的可渲染文本字幕流"""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "s",
                "-show_entries", "stream=index,codec_name:stream_tags=language,title",
                "-of", "json", video_path,
            ],
            capture_output=True,
            stdin=subprocess.DEVNULL,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as e:
        logger.error(f"[subtitle] ffprobe 读取内封字幕失败: {e}")
        return []

    if result.returncode != 0:
        logger.error(f"[subtitle] ffprobe 返回错误: {result.stderr.decode('utf-8', 'ignore')}")
        return []

    try:
        streams = json.loads(result.stdout.decode("utf-8", "ignore")).get("streams") or []
    except (ValueError, json.JSONDecodeError):
        return []

    subtitles = []
    order = 0
    for stream in streams:
        codec = (stream.get("codec_name") or "").lower()
        if codec not in _TEXT_SUB_CODECS:
            continue
        order += 1
        tags = stream.get("tags") or {}
        name = tags.get("title") or tags.get("language") or f"内封字幕 {order}"
        subtitles.append({
            "source": "internal",
            "name": name,
            "stream": stream.get("index"),
            "codec": codec,
        })
    return subtitles


def list_subtitles(video_path):
    """汇总字幕：外挂在前、内封在后"""
    return list_external_subtitles(video_path) + list_internal_subtitles(video_path)


def list_external_fonts(video_path):
    """扫描视频同目录及常见字体子目录下的外挂字体，供前端 ASS 渲染使用

    字幕组常把字体放在视频同目录或同目录的 fonts 子目录中；没有外挂字体时前端
    会回退到内置的默认中文字体。
    """
    directory = os.path.dirname(video_path)
    scan_dirs = [directory]
    for sub in _FONT_SUBDIRS:
        candidate = os.path.join(directory, sub)
        if os.path.isdir(candidate):
            scan_dirs.append(candidate)

    fonts = []
    for scan_dir in scan_dirs:
        try:
            names = os.listdir(scan_dir)
        except OSError as e:
            logger.error(f"[subtitle] 读取字体目录失败: {e}")
            continue
        for name in sorted(names):
            if os.path.splitext(name)[1].lower() not in _EXTERNAL_FONT_EXTS:
                continue
            font_path = os.path.join(scan_dir, name)
            if os.path.isfile(font_path):
                fonts.append({"name": name, "path": font_path})
    return fonts


def read_external_subtitle(sub_path):
    """读取外挂字幕文件内容，统一转成 utf-8 文本；失败返回 None"""
    try:
        with open(sub_path, "rb") as f:
            data = f.read()
    except OSError as e:
        logger.error(f"[subtitle] 读取外挂字幕失败: {e}")
        return None
    return _decode_bytes(data)


# 判断外挂字幕真实格式时只读文件头部（ASS 的 [Script Info] 一定在最前面）
_SUB_SNIFF_BYTES = 8192

# SRT 时间轴：00:00:17,100 --> 00:00:21,600
_SRT_TIME_RE = re.compile(r"\d{1,2}:\d{2}:\d{2}[,.]\d{1,3}\s*-->")


def detect_external_format(sub_path):
    """按文件内容判断外挂字幕真实格式（ass / srt / vtt），无法识别时退回扩展名

    不能只看扩展名：发布组把 SRT 内容存成 .ass 的情况很常见，而前端按类型选择渲染器
    （ass 交给 libass），判错会导致字幕渲染失败（libass 解析报错后整个渲染器都不可用）。
    """
    ext = os.path.splitext(sub_path)[1].lstrip(".").lower()
    fallback = "ass" if ext == "ssa" else (ext or "srt")
    try:
        with open(sub_path, "rb") as f:
            text = _decode_bytes(f.read(_SUB_SNIFF_BYTES))
    except (OSError, UnicodeDecodeError) as e:
        logger.error(f"[subtitle] 读取外挂字幕头部失败: {e}")
        return fallback

    head = text.lstrip("\ufeff").lstrip()
    if head.startswith("WEBVTT"):
        return "vtt"
    lowered = head.lower()
    if "[script info]" in lowered or "[events]" in lowered:
        return "ass"
    if _SRT_TIME_RE.search(head):
        return "srt"
    return fallback


def _cache_file(video_path, stream_index, ext):
    """按 路径 + 修改时间 + 大小 + 字幕流 + 格式 生成缓存文件路径，源文件变更后自动失效"""
    stat = os.stat(video_path)
    raw = f"{video_path}|{stat.st_mtime_ns}|{stat.st_size}|stream:{stream_index}|{ext}"
    key = hashlib.md5(raw.encode("utf-8")).hexdigest()
    cache_dir = os.path.join(get_base_path(), _CACHE_DIR_NAME)
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, f"{key}.{ext}")


def _sub_format(codec):
    """字幕流的输出格式：ASS 系列保留原样式输出为 ass，其余文本字幕统一输出为 srt

    前端 ASS 渲染器（libass/jassub）需要原始的 ass 文本，若先转成 srt 会丢失
    样式、定位与特效，因此内封 ASS 必须按 ass 输出。
    """
    return "ass" if codec in ("ass", "ssa") else "srt"


def _find_internal_stream(video_path, stream_index):
    """按流序号查找视频内的文本字幕流（stream_index 可能来自查询参数，故统一转字符串比较）"""
    for item in list_internal_subtitles(video_path):
        if str(item["stream"]) == str(stream_index):
            return item
    return None


def _read_cache(cache_file):
    try:
        with open(cache_file, "rb") as f:
            return _decode_bytes(f.read())
    except OSError:
        return None


def _remove_quietly(path):
    try:
        os.remove(path)
    except OSError:
        pass


def extract_internal_subtitle(video_path, stream_index):
    """返回指定内封字幕流的文本（ASS 系列返回 ass，其余返回 srt）

    ffmpeg 提取内封字幕必须从头扫描整个文件（mkv 字幕块与视频交错存放，无法跳读），
    逐条提取会导致每点一个字幕就重扫一遍。因此首次访问时用一条命令把该视频的
    **所有**内封字幕流一次性提取并缓存，之后任意切换都直接命中缓存。
    """
    stream = _find_internal_stream(video_path, stream_index)
    if stream is None:
        raise RuntimeError("未找到指定的内封字幕流")

    cache_file = _cache_file(video_path, stream_index, _sub_format(stream["codec"]))
    cached = _read_cache(cache_file)
    if cached is not None:
        return cached

    # 提取涉及整文件扫描，串行执行避免多请求并发抢占磁盘
    with _extract_lock:
        cached = _read_cache(cache_file)
        if cached is not None:
            return cached

        _extract_all_internal(video_path)

        cached = _read_cache(cache_file)
        if cached is None:
            raise RuntimeError("该字幕流提取失败")
        return cached


def start_internal_prefetch(video_path):
    """后台预热：打开播放页时提前提取并缓存该视频的全部内封字幕

    由调用方保证该视频确实存在内封字幕（没有则不必触发）。同一视频在提取完成前
    不会重复启动；提取过程与用户点击共用同一把锁，因此点击时要么等待预热完成，
    要么直接命中缓存。
    """
    with _prefetch_lock:
        if video_path in _prefetching:
            return
        _prefetching.add(video_path)

    def _worker():
        try:
            _extract_all_internal(video_path)
        except Exception as e:
            logger.warning(f"[subtitle] 内封字幕预热失败: {video_path} - {e}")
        finally:
            with _prefetch_lock:
                _prefetching.discard(video_path)

    threading.Thread(target=_worker, name="subtitle-prefetch", daemon=True).start()


def _extract_all_internal(video_path):
    """一次 ffmpeg 调用提取视频的全部内封文本字幕流到缓存文件

    ASS/SSA 流按 ass 输出以保留样式与特效，其余文本流统一转成 srt。
    """
    streams = list_internal_subtitles(video_path)
    pending = []
    for item in streams:
        ext = _sub_format(item["codec"])
        cache_file = _cache_file(video_path, item["stream"], ext)
        if not os.path.isfile(cache_file):
            pending.append((item["stream"], cache_file, ext))

    if not pending:
        return

    # 先写临时文件，全部成功后再改名，避免失败时留下半截缓存
    tmp_pairs = []
    args = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-i", video_path]
    for stream_index, cache_file, ext in pending:
        tmp_file = cache_file + ".tmp"
        tmp_pairs.append((tmp_file, cache_file))
        args += ["-map", f"0:{stream_index}", "-c:s", ext, "-f", ext, tmp_file]

    started = time.time()
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            timeout=_FFMPEG_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        for tmp_file, _ in tmp_pairs:
            _remove_quietly(tmp_file)
        logger.error(
            f"[subtitle] 提取内封字幕超时({_FFMPEG_TIMEOUT}s): {video_path}"
        )
        raise RuntimeError("提取字幕超时")
    except OSError as e:
        for tmp_file, _ in tmp_pairs:
            _remove_quietly(tmp_file)
        logger.error(f"[subtitle] ffmpeg 执行失败: {e}")
        raise RuntimeError(f"ffmpeg 不可用（{e}）")

    if result.returncode != 0:
        for tmp_file, _ in tmp_pairs:
            _remove_quietly(tmp_file)
        stderr_lines = [
            line for line in result.stderr.decode("utf-8", "ignore").splitlines()
            if line.strip()
        ]
        detail = stderr_lines[-1] if stderr_lines else "ffmpeg 提取字幕失败"
        logger.error(f"[subtitle] ffmpeg 提取内封字幕错误: {detail}")
        raise RuntimeError(detail)

    for tmp_file, cache_file in tmp_pairs:
        if os.path.isfile(tmp_file):
            os.replace(tmp_file, cache_file)

    logger.info(
        f"[subtitle] 提取内封字幕完成: {os.path.basename(video_path)} "
        f"共 {len(tmp_pairs)} 条，耗时 {time.time() - started:.1f}s"
    )
