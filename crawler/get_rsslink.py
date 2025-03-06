from api.api_qBittorrent import addFeed


def get_rss_link(bangumiId, subgroupid):
    base_url = "https://mikanani.me"
    rss_path = "/RSS"
    query_params_bangumi_id = "/Bangumi?bangumiId="
    query_params_subgroup_id = "&subgroupid="
    url = f"{base_url}{rss_path}{query_params_bangumi_id}{bangumiId}{query_params_subgroup_id}{subgroupid}"

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