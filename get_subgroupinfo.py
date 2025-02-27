import requests
from lxml import etree

def get_subgroup_info(bangumiId):
    try:
        http = "https://mikanani.me"
        search = "/Home/Bangumi/"
        subtitle_group_list_xpath = './/*[@id="sk-container"]/div[1]/div[3]/ul/li'
        subgroupId_element_xpath = './/span[1]/a/@data-anchor'
        subgroupname_element_xpath = './/span[1]/a/text()'

        url = f"{http}{search}{bangumiId}"

        response = requests.get(url)
        response.raise_for_status()

        # 使用 lxml 解析网页内容
        html = etree.HTML(response.content)
        subtitle_group_list = html.xpath(subtitle_group_list_xpath)

        data = []

        for i in subtitle_group_list :
            subgroupId_element = i.xpath(subgroupId_element_xpath)
            subgroupname_element = i.xpath(subgroupname_element_xpath)

            data.append({
                "subgroupId": subgroupId_element[0],
                "subgroupname": subgroupname_element[0]
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