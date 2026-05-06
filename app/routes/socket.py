from flask import Blueprint
from app.utils.auth import token_required
import os

socket_bp = Blueprint('socket', __name__)

@socket_bp.route('/', methods=['GET'])
def get_websocket_url(current_user):
    # ler o arquivo .env e pegar a url do websocket
    websocket_url = os.environ.get("PUBLIC_URL_WS")
    return {"url": websocket_url}, 200