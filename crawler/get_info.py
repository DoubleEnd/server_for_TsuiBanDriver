import json

import requests
import xmltodict
from lxml import etree

#获取id列表
def get_info_list(banguminame):
    try:
        base_url = "https://mikanani.me"
        home_path = "/Home"
        rss_path = "/RSS"
        query_params_bangumi_name = "/Search?searchstr="
        xpath_bangumi_list_item = "//*[@id='sk-container']/div[2]/ul/li"
        xpath_bangumi_id_href = './/a/@href'
        xpath_bangumi_img = './/a/span/@data-src'
        xpath_bangumi_title = './/a//div[@class="an-text"]/@title'

        url = f"{base_url}{home_path}{query_params_bangumi_name}{banguminame}"
        rss_url = f"{base_url}{rss_path}{query_params_bangumi_name}{banguminame}"

        response = requests.get(url)
        response.raise_for_status()

        html = etree.HTML(response.content)
        id_list = html.xpath(xpath_bangumi_list_item)

        response_rss = requests.get(rss_url)
        response_rss.raise_for_status()
        xml_content = response_rss.text
        # 将 XML 转换为 JSON
        convertJson = xmltodict.parse(xml_content, encoding='utf-8')
        jsonStr = json.dumps(convertJson, indent=1, ensure_ascii=False)

        data = {
            "bangumiItem": [],
            "rss": jsonStr
        }

        for i in id_list:
            # print(etree.tostring(i, encoding='utf-8').decode('utf-8'))
            bangumiId_element = i.xpath(xpath_bangumi_id_href)
            img_element = i.xpath(xpath_bangumi_img)
            title_element = i.xpath(xpath_bangumi_title)
            # for j in bangumiId_element:
            #     print(etree.tostring(j, encoding='utf-8').decode('utf-8'))
            # print(bangumiId_element)

            url_part = img_element[0] # 先通过 url( 分割，取第二个部分
            image_path = url_part.split('?')[0] # 再通过 ? 分割，取第一个部分

            data["bangumiItem"].append({
                "bangumiId": bangumiId_element[0].split('/')[-1],
                "img": base_url + image_path,
                "title": title_element[0],
                "rss_url": rss_url,
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
#         result = get_info_list(banguminame="进击的巨人")
#         if result is None:
#             sendInfo = {"code": 500, "msg": False, "data": "网络请求失败"}
#         else:
#             sendInfo = {"code": 200, "msg": "success", "data": result}
#     except Exception as e:
#         print(f"未知错误: {e}")
#         sendInfo = {"code": 500, "msg": False, "data": "未知错误"}
#     print(sendInfo)
