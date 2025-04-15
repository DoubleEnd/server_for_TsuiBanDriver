from utils.fun_request import api_qBittorrent_request


def login(data):
    return api_qBittorrent_request({
        "url": "auth/login",
        "method": "post",
        "data": data
    }).cookies


# def get_all_rss_items(params):
#     return request({
#         "url": "rss/items",
#         "method": "get",
#         "params": params
#     })
#
def addFeed(data):
    return api_qBittorrent_request({
        "url": "rss/addFeed",
        "method": "post",
        "data": data
    })
#
# def refreshItem(data):
#     return request({
#         "url": "rss/refreshItem",
#         "method": "post",
#         "data": data
#     })
#
# def removeItem(data):
#     return request({
#         "url": "rss/removeItem",
#         "method": "post",
#         "data": data
#     })
#
# def moveItem(data):
#     return request({
#         "url": "rss/moveItem",
#         "method": "post",
#         "data": data
#     })

def post_everything(config):
    return api_qBittorrent_request({
        "url": config['url'],
        "method": 'POST',
        "data": config['data']
    })

def get_everything(config):
    return api_qBittorrent_request({
        "url": config['url'],
        "method": 'GET',
        "params": config
    })

def set_rule(data):
    return api_qBittorrent_request({
        "url": 'rss/setRule',
        "method": 'POST',
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": data
    })

def get_version(data):
    return api_qBittorrent_request({
        "url": 'app/version',
        "method": 'GET',
        "params": data
    })

def get_webapiVersion(data):
    return api_qBittorrent_request({
        "url": 'app/webapiVersion',
        "method": 'GET',
        "params": data
    })

# if __name__ == '__main__':
#     fun_request.global_cookie = login({
#         'username': 'admin',
#         'password': '123456'
#     },)
    # print(get_all_rss_items({}).json())

