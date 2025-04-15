# server_for_TsuiBanDriver

## 简介
这是一个用于 TsuiBanDriver 的服务器端应用程序，它提供了多种功能，包括与 qBittorrent 和 dandanPlay 的交互，以及爬取字幕组信息和番剧信息。

## 功能
- 与 qBittorrent 的交互，包括登录、添加 RSS 订阅链接、获取所有信息、设置下载规则、获取 qBittorrent 版本信息和个人信息。
- 与 dandanPlay 的交互，包括欢迎、图书馆、番剧、番剧列表、获取字幕。
- 爬取字幕组信息和番剧信息。

## 文件结构
```
server_for_TsuiBanDriver
├── api
│   ├── api_dandanPlay.py
│   └── api_qBittorrent.py
├── app.py
├── assets
│   ├── app_info.json
│   ├── nginx.conf
│   ├── rule_config.json
│   ├── rule_info.json
│   └── url_config.json
├── crawler
│   ├── get_info.py
│   ├── get_rsslink.py
│   ├── get_subgroupinfo.py
│   └── get_subtitle.py
├── LICENSE.txt
├── README.md
└── utils
    ├── fun_config.py
    ├── fun_nginx.py
    └── fun_request.py
```

## API 文件
- `api_dandanPlay.py`: 包含与 dandanPlay 的交互函数。
- `api_qBittorrent.py`: 包含与 qBittorrent 的交互函数。

## 爬虫文件
- `get_info.py`: 包含获取番剧信息列表的函数。
- `get_rsslink.py`: 包含获取 RSS 链接的函数。
- `get_subgroupinfo.py`: 包含获取字幕组信息的函数。
- `get_subtitle.py`: 包含获取字幕的函数。

## 工具文件
- `fun_config.py`: 包含读取和保存配置文件的函数。
- `fun_nginx.py`: 包含与 Nginx 交互的函数。
- `fun_request.py`: 包含发送 HTTP 请求的函数。

## 配置文件
- `app_info.json`: 包含应用程序的信息。
- `nginx.conf`: 包含 Nginx 的配置。
- `rule_config.json`: 包含规则配置。
- `rule_info.json`: 包含规则信息。
- `url_config.json`: 包含 URL 配置。

## 许可证
本项目采用知识共享署名-非商业性使用 4.0 国际 (CC BY-NC 4.0) 许可证。

## 注意
请确保在使用本项目时遵守相关法律法规，不得用于非法用途。

## 贡献
如果您有任何建议或想要贡献代码，请随时提交 Pull Request 或创建 Issue。

## 联系方式
如有任何问题，请通过 GitHub Issues 提交。

---