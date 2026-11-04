# Bangumi.tv 公共接口请求：官方站 / 镜像站、带代理 / 直连依次尝试
import logging
import os
import threading
from datetime import datetime

import requests

from utils.config_manager import get_base_path, load_json_safe, save_json_safe
from utils.fun_request import request as fun_request

logger = logging.getLogger(__name__)

BGMI_API = "https://api.bgm.tv"
BGMI_MIRROR_API = "https://bgmapi.anibt.net"

# 时间表缓存文件：data/calendar_cache.json
_CALENDAR_CACHE_FILE = "calendar_cache.json"
# 时间表后台刷新互斥：同一时间只允许一个刷新任务，避免并发重复请求上游
_calendar_refreshing = threading.Lock()


class BangumiApiError(Exception):
    """Bangumi 公共接口全部尝试失败"""


def _build_attempts(use_mirror):
    sources = [("mirror", BGMI_MIRROR_API), ("official", BGMI_API)] if use_mirror else [("official", BGMI_API), ("mirror", BGMI_MIRROR_API)]
    attempts = []
    for source_name, base_url in sources:
        attempts.append((source_name, base_url, True))
    for source_name, base_url in sources:
        attempts.append((source_name, base_url, False))
    return attempts


def request_bangumi_api(rel_path, method="GET", params=None, data=None, headers=None, use_mirror=False, timeout=30):
    """请求 Bangumi 公共接口（官方站 / 镜像站、带代理 / 直连依次尝试）

    成功返回响应体：JSON 接口返回解析后的对象，其余返回文本。
    全部尝试失败时抛出 BangumiApiError。
    """
    last_error = None
    for source_name, base_url, use_proxy in _build_attempts(use_mirror):
        upstream_url = f"{base_url}/{rel_path}"
        try:
            logger.info(f"[bangumi] 请求 {method} {upstream_url} source={source_name} proxy={use_proxy}")
            response = fun_request(
                config={
                    "method": method.upper(),
                    "params": params or {},
                    "data": data if data is not None else {},
                    "headers": headers or {},
                    "timeout": timeout,
                },
                url=upstream_url,
                use_proxy=use_proxy,
            )

            if 200 <= response.status_code < 300:
                content_type = response.headers.get("Content-Type", "")
                if "application/json" in content_type.lower():
                    try:
                        return response.json()
                    except Exception as e:
                        # 代理可能导致响应体损坏，此时换下一个源（含直连）重试
                        last_error = f"响应无法解析为 JSON: {str(e)}"
                        logger.warning(f"[bangumi] {upstream_url} 解析失败，尝试下一个源 -> {last_error}")
                        continue
                logger.info(f"[bangumi] 成功 {method} {upstream_url} -> {response.status_code}")
                return response.text

            last_error = f"HTTP {response.status_code}: {response.text[:200]}"
            logger.warning(f"[bangumi] 上游失败 {method} {upstream_url} -> {last_error}")
        except requests.RequestException as e:
            last_error = str(e)
            logger.warning(
                f"[bangumi] 请求异常 {method} {upstream_url} "
                f"source={source_name} proxy={use_proxy}: {last_error}"
            )

    raise BangumiApiError(last_error or "未知错误")


def get_subject(subject_id, use_mirror=False):
    """取 Bangumi.tv 条目详情（名称、简介、封面、评分）"""
    return request_bangumi_api(f"subject/{subject_id}", use_mirror=use_mirror)


def get_calendar_cache_path():
    """时间表缓存路径：data/calendar_cache.json"""
    return os.path.join(get_base_path(), "data", _CALENDAR_CACHE_FILE)


def _load_calendar_cache():
    """读取时间表缓存，内容不可用时返回 None"""
    path = get_calendar_cache_path()
    if not os.path.isfile(path):
        return None
    data = load_json_safe(path)
    if isinstance(data, dict) and isinstance(data.get("days"), list) and data["days"]:
        return data
    return None


def _save_calendar_cache(days):
    save_json_safe(get_calendar_cache_path(), {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "days": days,
    })


def _refresh_calendar_cache(use_mirror):
    """后台刷新时间表缓存：请求最新数据并覆盖缓存，失败保留旧缓存"""
    if not _calendar_refreshing.acquire(blocking=False):
        # 已有刷新任务在进行，跳过本次，避免并发重复请求上游
        return
    try:
        body = request_bangumi_api("calendar", use_mirror=use_mirror)
        days = body if isinstance(body, list) else []
        if not days:
            logger.warning("[bangumi] 时间表刷新返回为空，保留旧缓存")
            return
        _save_calendar_cache(days)
        logger.info(f"[bangumi] 时间表缓存已刷新：{len(days)} 天")
    except Exception as e:
        logger.warning(f"[bangumi] 时间表缓存刷新失败，保留旧缓存: {e}")
    finally:
        _calendar_refreshing.release()


def get_calendar(use_mirror=False):
    """番剧时间表：有缓存就立即返回缓存，同时后台请求最新数据覆盖缓存

    没有缓存时同步请求一次（此时才需要等网络），并写入缓存。
    """
    cache = _load_calendar_cache()
    if cache:
        threading.Thread(
            target=_refresh_calendar_cache,
            args=(use_mirror,),
            daemon=True,
        ).start()
        return cache["days"]

    body = request_bangumi_api("calendar", use_mirror=use_mirror)
    days = body if isinstance(body, list) else []
    if days:
        _save_calendar_cache(days)
    return days
