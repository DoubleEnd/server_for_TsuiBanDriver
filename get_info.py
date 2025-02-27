import requests
from lxml import etree

#获取id列表
def get_info_list(banguminame):
    try:
        http = "https://mikanani.me"
        search = "/Home/Search?searchstr="
        list_item_xpath = "//*[@id='sk-container']/div[2]/ul/li"
        bangumiId_element_xpah = './/a/@href'
        img_element_xpah = './/a/span/@data-src'
        title_element_xpah = './/a//div[@class="an-text"]/@title'

        url = f"{http}{search}{banguminame}"

        response = requests.get(url)
        response.raise_for_status()

        # 使用 lxml 解析网页内容
        html = etree.HTML(response.content)
        id_list = html.xpath(list_item_xpath)
        # print(id_list)

        data = []

        for i in id_list:
            print(etree.tostring(i, encoding='utf-8').decode('utf-8'))
            bangumiId_element = i.xpath(bangumiId_element_xpah)
            img_element = i.xpath(img_element_xpah)
            title_element = i.xpath(title_element_xpah)
            # for j in bangumiId_element:
            #     print(etree.tostring(j, encoding='utf-8').decode('utf-8'))
            # print(bangumiId_element)

            url_part = img_element[0] # 先通过 url( 分割，取第二个部分
            image_path = url_part.split('?')[0] # 再通过 ? 分割，取第一个部分

            data.append({
                "bangumiId": bangumiId_element[0].split('/')[-1],
                "img": http+image_path,
                "title": title_element[0]
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

    # print(sendInfo)
