import requests
from lxml import etree

#获取id列表
def get_info_list(banguminame):
    try:
        http = "https://mikanani.me"
        search = "/Home/Search?searchstr="
        url = f"{http}{search}{banguminame}"

        response = requests.get(url)
        response.raise_for_status()

        # 使用 lxml 解析网页内容
        html = etree.HTML(response.content)
        len_id_list = len(html.xpath(f'//*[@id="sk-container"]/div[2]/ul/li'))

        data = []

        for i in range(1,len_id_list+1):
            bangumiId_element = html.xpath(f'//*[@id="sk-container"]/div[2]/ul/li[{i}]/a/@href')
            img_element = html.xpath(f'//*[@id="sk-container"]/div[2]/ul/li[{i}]//a/span/@data-src')
            title_element = html.xpath(f'//*[@id="sk-container"]/div[2]/ul/li[{i}]/a//div[@class="an-text"]/@title')
            # print(etree.tostring(img_element[0], encoding='utf-8').decode('utf-8'))

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
#         result = get_info_list(moviename="进击的巨人")
#         if result is None:
#             sendInfo = {"code": 500, "msg": False, "data": "网络请求失败"}
#         else:
#             sendInfo = {"code": 200, "msg": "success", "data": result}
#     except Exception as e:
#         print(f"未知错误: {e}")
#         sendInfo = {"code": 500, "msg": False, "data": "未知错误"}
#
#     print(sendInfo)
