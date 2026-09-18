# Bangumi 相关路由
import logging

import requests
from flask import Blueprint, request

from utils.fun_request import request as fun_request
from utils.fun_response import success, error

logger = logging.getLogger(__name__)
bangumi_bp = Blueprint('bangumi', __name__)

BGMI_API = "https://api.bgm.tv"
BGMI_MIRROR_API = "https://bgmapi.anibt.net"

ALLOWED_METHODS = ["GET", "POST", "PUT", "DELETE", "HEAD", "PATCH", "OPTIONS"]


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
                logger.info(f"[bangumi] 成功 {method} {upstream_url} -> {response.status_code}")
                content_type = response.headers.get("Content-Type", "")
                if "application/json" in content_type.lower():
                    try:
                        return response.json()
                    except Exception as e:
                        logger.warning(f"[bangumi] 解析响应失败, 返回原文: {str(e)}")
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


@bangumi_bp.route("/proxy/<path:subpath>", methods=ALLOWED_METHODS)
def bangumi_proxy(subpath):
    use_mirror = request.args.get("useMirror", "false").lower() == "true"
    method = request.method.upper()
    if method not in ALLOWED_METHODS:
        return error("请求方法不被允许", 405)

    upstream_params = {k: v for k, v in request.args.items() if k.lower() != "usemirror"}
    upstream_headers = {k: v for k, v in request.headers.items()
                        if k.lower() not in ("host", "content-length", "cookie", "authorization")}
    content_type = request.headers.get("Content-Type", "")

    if content_type.startswith("application/json") or request.is_json:
        json_data = request.get_json(silent=True)
        upstream_data = json_data if json_data is not None else request.get_data()
    else:
        upstream_data = request.get_data()

    logger.info(f"[bangumi/proxy] {method} {subpath} 镜像优先: {use_mirror}")

    try:
        body = request_bangumi_api(
            subpath,
            method=method,
            params=upstream_params,
            data=upstream_data,
            headers=upstream_headers,
            use_mirror=use_mirror,
        )
        return success(body)
    except BangumiApiError as e:
        return error("请求 Bangumi API 失败", 502, msg=str(e))
    except Exception as e:
        logger.error(f"[bangumi/proxy] 异常错误 {method} {subpath}: {str(e)}", exc_info=True)
        return error("请求 Bangumi API 失败", 500, msg=str(e))
