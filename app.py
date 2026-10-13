import atexit
import logging

from flask import Flask
from flask_cors import CORS

from routes import register_blueprints
from utils import fun_scan
from utils.fun_logger import archive_log, log_startup_info, setup_logging

logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# 注册所有路由 Blueprint
register_blueprints(app)

if __name__ == "__main__":
    # 日志：实时写 logs/backend.log，退出时归档到 logs/archive/
    setup_logging()
    atexit.register(archive_log)

    logger.info("[启动] 启动应用服务器...")
    log_startup_info()

    # 周期自动扫描：后台线程按配置间隔触发快速扫描（只处理新文件）
    fun_scan.start_auto_scan()

    # 关闭重载器：Windows 下重载器会强杀子进程，导致退出时的日志归档无法执行
    app.run(host="0.0.0.0", debug=True, use_reloader=False)
