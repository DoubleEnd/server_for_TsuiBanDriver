import requests
from lxml import etree

def get_subgroup_info(bangumiId):
    try:
        base_url = "https://mikanani.me"
        home_path = "/Home"
        bangumi_path = "/Bangumi/"
        xpath_subgroup_list = './/*[@id="sk-container"]/div[1]/div[3]/ul/li'
        xpath_subgroup_id = './/span[1]/a/@data-anchor'
        xpath_subgroup_name = './/span[1]/a/text()'

        url = f"{base_url}{home_path}{bangumi_path}{bangumiId}"

        response = requests.get(url)
        response.raise_for_status()

        # 使用 lxml 解析网页内容
        html = etree.HTML(response.content)
        subgroup_list = html.xpath(xpath_subgroup_list)

        data = []

        for i in subgroup_list :
            subgroup_id = i.xpath(xpath_subgroup_id)
            subgroup_name = i.xpath(xpath_subgroup_name)

            data.append({
                "subgroupId": subgroup_id[0],
                "subgroupname": subgroup_name[0]
            })

        return data

    except requests.exceptions.RequestException as e:
        print(f"请求出错: {e}")
        return None  # 在请求出错时返回 None
    except Exception as e:
        print(f"解析出错: {e}")
        return None  # 在解析出错时返回 None

# if __name__ == "__main__":
#     try:
#         result = get_subgroup_info(bangumiId="1678")
#         if result is None:
#             sendInfo = {"code": 500, "msg": False, "data": "网络请求失败"}
#         else:
#             sendInfo = {"code": 200, "msg": "success", "data": result}
#     except Exception as e:
#         print(f"未知错误: {e}")
#         sendInfo = {"code": 500, "msg": False, "data": "未知错误"}
#
#     print(sendInfo)