# Bangumi.tv 公共接口请求：官方站 / 镜像站、带代理 / 直连依次尝试
import logging

import requests

from utils.fun_request import request as fun_request

logger = logging.getLogger(__name__)

BGMI_API = "https://api.bgm.tv"
BGMI_MIRROR_API = "https://bgmapi.anibt.net"


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
