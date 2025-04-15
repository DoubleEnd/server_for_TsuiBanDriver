from api.api_qBittorrent import addFeed
from utils.fun_config import match_rule


def get_rss_link(bangumiId, subgroupid):
    rule = match_rule()
    base_url = rule["base_url"]
    rss_path = rule["rss_path"]
    query_params_bangumi_id = rule["query_params_bangumi_id"]
    query_params_subgroup_id = rule["query_params_subgroup_id"]
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