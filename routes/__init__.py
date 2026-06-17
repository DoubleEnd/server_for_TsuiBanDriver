# routes/__init__.py - 注册所有 Blueprint
from .search import search_bp
from .qbittorrent import qbittorrent_bp
from .dandanplay import dandanplay_bp
from .config import config_bp
from .ai import ai_bp


def register_blueprints(app):
    app.register_blueprint(search_bp)
    app.register_blueprint(qbittorrent_bp)
    app.register_blueprint(dandanplay_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(ai_bp)
