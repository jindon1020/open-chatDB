import os
import sys
from flask import Flask, send_from_directory
from asgiref.wsgi import WsgiToAsgi
from config import Config
from routes.api_connections import connections_bp
from routes.api_database import database_bp
from routes.api_query import query_bp
from routes.api_schema import schema_bp
from routes.api_chat import chat_bp
from routes.api_settings import settings_bp
from services import settings_manager


def _base_dir():
    """Return the project root, accounting for PyInstaller bundles."""
    if getattr(sys, '_MEIPASS', None):
        return sys._MEIPASS
    return os.path.dirname(__file__)


def create_app():
    base = _base_dir()
    app = Flask(
        __name__,
        static_folder=os.path.join(base, "static"),
        template_folder=os.path.join(base, "templates"),
    )
    app.config.from_object(Config)

    os.makedirs(Config.DATA_DIR, exist_ok=True)

    # Load persisted LLM settings into Config
    settings_manager.load()

    # Register blueprints
    app.register_blueprint(connections_bp, url_prefix="/api/connections")
    app.register_blueprint(database_bp, url_prefix="/api/db")
    app.register_blueprint(query_bp, url_prefix="/api/query")
    app.register_blueprint(schema_bp, url_prefix="/api/schema")
    app.register_blueprint(chat_bp, url_prefix="/api/chat")
    app.register_blueprint(settings_bp, url_prefix="/api/settings")

    @app.route("/")
    def index():
        return send_from_directory(app.template_folder, "index.html")

    return app


application = create_app()
asgi_app = WsgiToAsgi(application)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(asgi_app, host="0.0.0.0", port=5001)
