from flask import Flask
from flask_cors import CORS
from config import config_dict
from .services.supabase_service import init_supabase
from .services.message_queue_service import init_message_worker
from .services.swagger import init_swagger
import os

def create_app():
    app = Flask(__name__)
    CORS(app, origins=os.environ.get("CORS_ORIGINS", "*").split(","))
    env = os.environ.get("FLASK_ENV", "development")
    app.config.from_object(config_dict[env])

    init_supabase(app)
    init_message_worker()
    init_swagger(app)

    # Registro de Blueprints
    from .routes.socket import socket_bp
    from .routes.chat_socket import sock
    from .routes.auth import auth_bp
    from .routes.health import health_bp
    from .routes.tour import tour_bp
    from .routes.message import messages_bp
    from .routes.request import request_bp
    from .routes.chat import chat_bp
    from .routes.pages import pages_bp
    from .routes.cidades import cidades_bp
    from .routes.favorite import favorite_bp
    from .routes.user import user_bp
    from .routes.locais import locais_bp
    from .routes.busca import busca_bp
    from .routes.avisos import avisos_bp

    app.register_blueprint(socket_bp, url_prefix='/ws')
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(health_bp, url_prefix='/health')
    app.register_blueprint(tour_bp, url_prefix='/tour')
    app.register_blueprint(messages_bp, url_prefix='/messages')
    app.register_blueprint(request_bp, url_prefix='/request')
    app.register_blueprint(chat_bp, url_prefix='/chat')
    app.register_blueprint(pages_bp, url_prefix='/pages')
    app.register_blueprint(cidades_bp, url_prefix='/cidades')
    app.register_blueprint(favorite_bp, url_prefix='/favorite')
    app.register_blueprint(user_bp, url_prefix='/users')
    app.register_blueprint(locais_bp, url_prefix='/locais')
    app.register_blueprint(busca_bp, url_prefix='/busca')
    app.register_blueprint(avisos_bp, url_prefix='/avisos')
    sock.init_app(app)

    return app