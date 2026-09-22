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

def get_rss_items(params=None):
    return api_qBittorrent_request({
        "url": "rss/items",
        "method": "get",
        "params": params or {}
    })

def get_rss_rules(params=None):
    return api_qBittorrent_request({
        "url": "rss/rules",
        "method": "get",
        "params": params or {}
    })

def add_torrents(data):
    """添加下载任务，data 包含 urls, savepath 等"""
    return api_qBittorrent_request({
        "url": "torrents/add",
        "method": "post",
        "data": data
    })

def get_torrents_info(params=None):
    """获取种子列表"""
    return api_qBittorrent_request({
        "url": "torrents/info",
        "method": "get",
        "params": params or {}
    })

def remove_item(data):
    return api_qBittorrent_request({
        "url": "rss/removeItem",
        "method": "post",
        "data": data
    })

def refresh_item(data):
    return api_qBittorrent_request({
        "url": "rss/refreshItem",
        "method": "post",
        "data": data
    })

def move_item(data):
    return api_qBittorrent_request({
        "url": "rss/moveItem",
        "method": "post",
        "data": data
    })

def mark_as_read(data):
    return api_qBittorrent_request({
        "url": "rss/markAsRead",
        "method": "post",
        "data": data
    })

def delete_torrents(data):
    return api_qBittorrent_request({
        "url": "torrents/delete",
        "method": "post",
        "data": data
    })

def matching_articles(params=None):
    return api_qBittorrent_request({
        "url": "rss/matchingArticles",
        "method": "get",
        "params": params or {}
    })

def remove_rule(data):
    return api_qBittorrent_request({
        "url": "rss/removeRule",
        "method": "post",
        "data": data
    })

def set_location(data):
    return api_qBittorrent_request({
        "url": "torrents/setLocation",
        "method": "post",
        "data": data
    })

# 种子动作 -> qBittorrent 接口（qBittorrent 5.0 起 pause/resume 改名为 stop/start，做回退兼容）
_TORRENT_ACTION_URLS = {
    "pause": ("torrents/pause", "torrents/stop"),
    "resume": ("torrents/resume", "torrents/start"),
    "forceStart": ("torrents/setForceStart",),
    "recheck": ("torrents/recheck",),
    "reannounce": ("torrents/reannounce",),
}

def torrents_action(action, data):
    """执行种子动作（暂停/启动/强制启动/强制校验/重新汇报），动作不支持时返回 None"""
    urls = _TORRENT_ACTION_URLS.get(action)
    if not urls:
        return None
    result = None
    for url in urls:
        result = api_qBittorrent_request({
            "url": url,
            "method": "post",
            "data": data
        })
        # 404 说明当前 qBittorrent 版本不认这个接口名，尝试下一个（如 5.0 的改名）
        if result.status_code != 404:
            return result
    return result

def get_sync_maindata(params=None):
    return api_qBittorrent_request({
        "url": "sync/maindata",
        "method": "get",
        "params": params or {}
    })

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

