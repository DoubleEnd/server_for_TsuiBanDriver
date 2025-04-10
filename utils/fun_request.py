import requests

global_cookie = ''
qBittorrent_BASE_URL = 'http://100.65.133.102:8080/api/v2/'
dandanPlay_BASE_URL = 'http://100.65.133.102:8888'

def api_qBittorrent_request(config):
    url = qBittorrent_BASE_URL + config.get('url', '')
    return request(config,url)

def api_dandanPlay_request(config):
    url = dandanPlay_BASE_URL + config.get('url', '')
    # print(url)
    return request(config, url)


def request(config, url):
    method = config.get('method', 'GET').upper()
    params = config.get('params', {})
    headers = config.get('headers', {})
    data = config.get('data', {})
    # stream = config.get('stream', False)

    try:
        if method == 'GET':
            response = requests.get(url, params=params, cookies=global_cookie, headers=headers)
        elif method == 'POST':
            response = requests.post(url, params=params, data=data, cookies=global_cookie, headers=headers)
        elif method == 'PUT':
            response = requests.put(url, params=params, data=data, cookies=global_cookie, headers=headers)
        elif method == 'DELETE':
            response = requests.delete(url, params=params, cookies=global_cookie, headers=headers)
        elif method == 'HEAD':
            response = requests.head(url, params=params, cookies=global_cookie, headers=headers)
        else:
            raise ValueError(f"该请求方式: {method} 不被支持")

        if response.status_code == 401:
            # 处理登录状态过期的情况
            pass
        return response
    except requests.RequestException as e:
        raise e