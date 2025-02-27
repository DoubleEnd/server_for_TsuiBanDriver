import fun_request
from api_qBittorrent import addFeed


def get_rss_link(banguminame, subgroupid):
    http = "https://mikanani.me"
    search = "/RSS/Search?searchstr="
    search_subgroupid = "&subgroupid="
    url = f"{http}{search}{banguminame}{search_subgroupid}{subgroupid}"
    data = {
        "url": url,
        "path":"",
    }
    addFeed(data)

    return {"code": 200, "msg": "success"}

# if __name__ == '__main__':
#     fun_request.global_cookie = login({
#         'username': 'admin',
#         'password': '123456'
#     }, )
#     get_rss_link("命运石之门", "1")