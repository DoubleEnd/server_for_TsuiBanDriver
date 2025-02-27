import requests

global_cookie = ''
BASE_URL = 'http://100.65.133.102:8080/api/v2/'

def request(config):

    url = BASE_URL + config.get('url', '')
    method = config.get('method', 'GET')
    params = config.get('params', {})
    data = config.get('data', {})

    try:
        if method.upper() == 'GET':
            response = requests.get(url, params=params, cookies=global_cookie)
        elif method.upper() == 'POST':
            response = requests.post(url, params=params, data=data, cookies=global_cookie)
        elif method.upper() == 'PUT':
            response = requests.put(url, params=params, data=data, cookies=global_cookie)
        elif method.upper() == 'DELETE':
            response = requests.delete(url, params=params, cookies=global_cookie)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        if response.status_code == 401:
            # 处理登录状态过期的情况
            pass
        else:
            return response
    except requests.RequestException as e:
        raise e
