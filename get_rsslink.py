import fun_request
from api_qBittorrent import addFeed


def get_rss_link(bangumiId, subgroupid):
    http = "https://mikanani.me"
    search_bangumiId = "/RSS/Bangumi?bangumiId="
    search_subgroupid = "&subgroupid="
    url = f"{http}{search_bangumiId}{bangumiId}{search_subgroupid}{subgroupid}"

    data = {
        "url": url,
        "path":"",
    }

    return addFeed(data)

# if __name__ == '__main__':
#     fun_request.global_cookie = login({
#         'username': 'admin',
#         'password': '123456'
#     }, )
#     get_rss_link("命运石之门", "1")