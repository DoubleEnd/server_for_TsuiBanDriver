# routes/__init__.py - 注册所有 Blueprint
from .search import search_bp
from .qbittorrent import qbittorrent_bp
from .media import media_bp
from .library import library_bp
from .user import user_bp
from .config import config_bp
from .ai import ai_bp
from .bangumi import bangumi_bp
from .auth import auth_bp


def register_blueprints(app):
    app.register_blueprint(search_bp)
    app.register_blueprint(qbittorrent_bp)
    app.register_blueprint(media_bp)
    app.register_blueprint(library_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(bangumi_bp)
    app.register_blueprint(auth_bp)
