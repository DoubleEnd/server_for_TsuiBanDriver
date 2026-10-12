import base64
import hashlib
import time

import requests
import urllib3

from utils.fun_config import get_url_config, get_search_config

# 禁用 SSL 证书验证警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 弹弹play 开放 API 地址（签名模式）
DANDANPLAY_API_BASE = "https://api.dandanplay.net"

# 用于缓存登录 cookie
_qb_cookie_cache = None


def get_qb_cookie():
    """获取 qBittorrent 登录 cookie，如果已缓存则返回缓存"""
    global _qb_cookie_cache
    if _qb_cookie_cache:
        return _qb_cookie_cache
    
    # 需要时才进行登录
    from api.api_qBittorrent import login
    url_config = get_url_config()
    try:
        cookie = login({
            'username': url_config.get('qBittorrent_username', 'admin'),
            'password': url_config.get('qBittorrent_password', '123456')
        })
        _qb_cookie_cache = cookie
        return cookie
    except Exception as e:
        print(f"qBittorrent 登录失败: {e}")
        return ''


def clear_qb_cookie_cache():
    """清除 qBittorrent cookie 缓存"""
    global _qb_cookie_cache
    _qb_cookie_cache = None


def get_qBittorrent_BASE_URL():
    """动态获取 qBittorrent BASE URL"""
    config = get_url_config()
    if config is None:
        return 'http://127.0.0.1:8080/api/v2/'
    return config['qBittorrent_BASE_URL']


def get_request_config(use_proxy=True):
    """获取搜索配置中的请求头和代理设置
    
    Args:
        use_proxy: 是否使用代理（qBittorrent 等局域网服务不需要代理）
    """
    search_config = get_search_config()
    config = {}
    
    # 设置请求头
    if search_config.get('search_header'):
        config['headers'] = {'User-Agent': search_config['search_header']}
    else:
        config['headers'] = {'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"}
    
    # 设置代理
    config['proxies'] = None
    if use_proxy and search_config.get('proxy_enabled'):
        proxy_host = search_config.get('proxy_host', '')
        proxy_port = search_config.get('proxy_port', '')
        proxy_protocol = search_config.get('proxy_protocol', 'http').lower()
        
        if proxy_host and proxy_port:
            # 构建代理URL，支持 http 和 socks5 协议
            if proxy_protocol == 'socks5':
                proxy_url = f"socks5h://{proxy_host}:{proxy_port}"
            else:
                # 默认使用 http
                proxy_url = f"http://{proxy_host}:{proxy_port}"
            
            config['proxies'] = {
                'http': proxy_url,
                'https': proxy_url
            }
    
    return config


def api_qBittorrent_request(config):
    """qBittorrent 请求（不使用代理）"""
    url = get_qBittorrent_BASE_URL() + config.get('url', '')
    # 登录接口不需要 cookie，否则会无限递归
    if config.get('url') == 'auth/login':
        cookie = ''
    else:
        cookie = get_qb_cookie()
    original_cookie = config.get('cookie', '')
    config['cookie'] = cookie
    result = request(config, url, use_proxy=False)
    config['cookie'] = original_cookie
    return result


def is_dandanplay_configured():
    """是否已配置弹弹play 开放 API 凭证（签名模式）"""
    config = get_url_config() or {}
    app_id = str(config.get("dandanPlay_app_id") or "").strip()
    app_secret = str(config.get("dandanPlay_app_secret") or "").strip()
    return bool(app_id and app_secret)


def dandanplay_signature_headers(path):
    """生成签名模式请求头：X-AppId + X-Timestamp + X-Signature

    算法：base64(sha256(AppId + Timestamp + Path + AppSecret))，
    Path 为接口路径且不含查询参数。未配置凭证时返回空字典。
    """
    config = get_url_config() or {}
    app_id = str(config.get("dandanPlay_app_id") or "").strip()
    app_secret = str(config.get("dandanPlay_app_secret") or "").strip()
    if not app_id or not app_secret:
        return {}
    timestamp = str(int(time.time()))
    raw = f"{app_id}{timestamp}{path}{app_secret}"
    signature = base64.b64encode(hashlib.sha256(raw.encode("utf-8")).digest()).decode()
    return {"X-AppId": app_id, "X-Timestamp": timestamp, "X-Signature": signature}


def api_dandanPlay_request(config):
    """弹弹play 开放 API 请求（签名模式，直连）"""
    path = config.get('url', '')
    headers = dict(config.get('headers') or {})
    headers.update(dandanplay_signature_headers(path))
    config['headers'] = headers
    return request(config, DANDANPLAY_API_BASE + path, use_proxy=False)


def post_or_put(sender, url, params, json_body, data, cookie, headers, proxies, timeout, verify_ssl):
    """POST/PUT 请求：有 json 体时以 JSON 发送，否则按表单发送"""
    common = dict(params=params, cookies=cookie, headers=headers,
                  proxies=proxies, timeout=timeout, verify=verify_ssl)
    if json_body is not None:
        return sender(url, json=json_body, **common)
    return sender(url, data=data, **common)


def request(config, url, use_proxy=True):
    """通用请求函数
    
    Args:
        config: 请求配置字典
        url: 完整的 URL
        use_proxy: 是否使用代理
    """
    method = config.get('method', 'GET').upper()
    params = config.get('params', {})
    headers = config.get('headers', {})
    data = config.get('data', {})
    # json 存在时以 JSON 方式发送请求体（如弹弹play 的 match 接口）
    json_body = config.get('json')
    cookie = config.get('cookie', '')
    timeout = config.get('timeout', 15)
    
    # 获取搜索配置中的请求设置
    search_request_config = get_request_config(use_proxy=use_proxy)
    
    # 合并请求头：优先使用传入的headers，否则使用配置中的
    if not headers:
        headers = search_request_config.get('headers', {})
    else:
        # 合并headers，传入的优先级更高
        default_headers = search_request_config.get('headers', {})
        headers = {**default_headers, **headers}
    
    # 获取代理设置
    proxies = search_request_config.get('proxies')
    
    # 判断是否需要禁用 SSL 证书验证
    # 当使用代理访问 HTTPS 时，需要禁用 SSL 证书验证以避免握手失败
    verify_ssl = True
    if use_proxy and proxies and url.startswith('https://'):
        verify_ssl = False

    try:
        if method == 'GET':
            response = requests.get(url, params=params, cookies=cookie, headers=headers, proxies=proxies, timeout=timeout, verify=verify_ssl)
        elif method == 'POST':
            response = post_or_put(requests.post, url, params, json_body, data, cookie, headers, proxies, timeout, verify_ssl)
        elif method == 'PUT':
            response = post_or_put(requests.put, url, params, json_body, data, cookie, headers, proxies, timeout, verify_ssl)
        elif method == 'DELETE':
            response = requests.delete(url, params=params, cookies=cookie, headers=headers, proxies=proxies, timeout=timeout, verify=verify_ssl)
        elif method == 'HEAD':
            response = requests.head(url, params=params, cookies=cookie, headers=headers, proxies=proxies, timeout=timeout, verify=verify_ssl)
        else:
            raise ValueError(f"该请求方式: {method} 不被支持")

        if response.status_code == 401:
            # 处理登录状态过期的情况
            pass
        return response
    except requests.RequestException as e:
        raise e