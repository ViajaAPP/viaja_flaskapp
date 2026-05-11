from flask import Blueprint
from app.utils.auth import token_required
import os

socket_bp = Blueprint('socket', __name__)

@socket_bp.route('/', methods=['GET'])
def get_websocket_url():
    # ler o arquivo .env e pegar a url do websocket
    websocket_url = None
    env_path = ".env"
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if line.startswith("PUBLIC_URL_WS="):
                    websocket_url = line.strip().split("=", 1)[1]
                    break
    return {"url": websocket_url}, 200