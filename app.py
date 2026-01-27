import os
from flask import Flask, send_from_directory
from asgiref.wsgi import WsgiToAsgi
from config import Config
from routes.api_connections import connections_bp
from routes.api_database import database_bp
from routes.api_query import query_bp
from routes.api_schema import schema_bp
from routes.api_chat import chat_bp


def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(Config)

    os.makedirs(Config.DATA_DIR, exist_ok=True)

    # Register blueprints
    app.register_blueprint(connections_bp, url_prefix="/api/connections")
    app.register_blueprint(database_bp, url_prefix="/api/db")
    app.register_blueprint(query_bp, url_prefix="/api/query")
    app.register_blueprint(schema_bp, url_prefix="/api/schema")
    app.register_blueprint(chat_bp, url_prefix="/api/chat")

    @app.route("/")
    def index():
        return send_from_directory("templates", "index.html")

    return app


application = create_app()
asgi_app = WsgiToAsgi(application)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(asgi_app, host="0.0.0.0", port=5001)
