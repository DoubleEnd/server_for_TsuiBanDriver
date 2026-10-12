# server_for_TsuiBanDriver

## 简介
这是一个用于 TsuiBanDriver 的服务器端应用程序，它提供了多种功能，包括与 qBittorrent 的交互、本地媒体库扫描，以及爬取字幕组信息和番剧信息。

## 功能
- 与 qBittorrent 的交互，包括登录、添加 RSS 订阅链接、获取所有信息、设置下载规则、获取 qBittorrent 版本信息和个人信息。
- 本地媒体库扫描：按配置的扫描目录与黑名单正则扫描本地视频，结果保存到 data/library.json。
- 本地媒体播放：视频直读、封面/缩略图生成、外挂与内封字幕、外挂字体。
- 爬取字幕组信息和番剧信息。

## 文件结构
```
server_for_TsuiBanDriver
├── api
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
│   └── get_subgroupinfo.py
├── LICENSE.txt
├── README.md
└── utils
    ├── fun_config.py
    ├── fun_nginx.py
    ├── fun_scan.py
    └── fun_request.py
```

## API 文件
- `api_qBittorrent.py`: 包含与 qBittorrent 的交互函数。

## 爬虫文件
- `get_info.py`: 包含获取番剧信息列表的函数。
- `get_rsslink.py`: 包含获取 RSS 链接的函数。
- `get_subgroupinfo.py`: 包含获取字幕组信息的函数。

## 工具文件
- `fun_config.py`: 包含读取和保存配置文件的函数。
- `fun_nginx.py`: 包含与 Nginx 交互的函数。
- `fun_scan.py`: 包含本地媒体库扫描的函数。
- `fun_request.py`: 包含发送 HTTP 请求的函数。

## 配置文件
- `app_info.json`: 包含应用程序的信息。
- `nginx.conf`: 包含 Nginx 的配置。
- `rule_config.json`: 包含规则配置。
- `rule_info.json`: 包含规则信息。
- `url_config.json`: 包含 URL 配置。
- `scan_config.json`: 包含扫描目录与黑名单配置。

## 许可证
本项目采用 AGPL-3.0 许可证。有关详细信息，请查看 LICENSE 文件。

## 注意
请确保在使用本项目时遵守相关法律法规，不得用于非法用途。

## 贡献
如果您有任何建议或想要贡献代码，请随时提交 Pull Request 或创建 Issue。

## 联系方式
如有任何问题，请通过 GitHub Issues 提交。

---