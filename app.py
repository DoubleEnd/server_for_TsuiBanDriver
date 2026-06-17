import logging

from flask import Flask
from flask_cors import CORS

from routes import register_blueprints

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# 注册所有路由 Blueprint
register_blueprints(app)

if __name__ == "__main__":
    logger.info("[启动] 启动应用服务器...")
    app.run(host="0.0.0.0", debug=True)
