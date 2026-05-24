from flask import Blueprint
from app.utils.auth import token_required
import os

socket_bp = Blueprint('socket', __name__)

def _get_websocket_url():
    """Lê a URL do WebSocket do arquivo .env."""
    websocket_url = None
    env_path = ".env"
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if line.startswith("PUBLIC_URL_WS="):
                    websocket_url = line.strip().split("=", 1)[1]
                    break
    return websocket_url

@socket_bp.route('/', methods=['GET'])
def get_websocket_url():
    """
    Obter a URL do WebSocket para conexões em tempo real
    ---
    tags:
        - Socket
    responses:
        200:
            description: URL do WebSocket obtida com sucesso
        404:
            description: URL do WebSocket não encontrada
    """
    websocket_url = _get_websocket_url()
    if websocket_url:
        return {"url": websocket_url}, 200
    else:
        return {"error": "URL do WebSocket não encontrada"}, 404