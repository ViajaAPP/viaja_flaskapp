from flask import Flask
from flask_cors import CORS
from config import config_dict
from .services.supabase_service import init_supabase
from .services.message_queue_service import init_message_worker
from .services.swagger import init_swagger
import os

def create_app():
    app = Flask(__name__)
    CORS(app)
    env = os.environ.get("FLASK_ENV", "development")
    app.config.from_object(config_dict[env])

    init_supabase(app)
    init_message_worker()
    init_swagger(app)

    # Registro de Blueprints
    from .routes.auth import auth_bp
    from .routes.health import health_bp
    from .routes.tour import tour_bp
    from .routes.message import messages_bp
    from .routes.request import request_bp
    from .routes.socket import socket_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(health_bp, url_prefix='/health')
    app.register_blueprint(tour_bp, url_prefix='/tour')
    app.register_blueprint(messages_bp, url_prefix='/messages')
    app.register_blueprint(request_bp, url_prefix='/request')
    app.register_blueprint(socket_bp, url_prefix='/ws')

    return app