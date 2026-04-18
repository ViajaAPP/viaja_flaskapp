from flask import Blueprint, request, jsonify
from app.services.message_queue_service import enqueue_message
from app.utils.auth import token_required

messages_bp = Blueprint('messages', __name__)

@messages_bp.route('/send', methods=['POST'])
@token_required
def send_message(current_user_id):
    data = request.json
    content = data.get('content')
    chat_id = data.get('chat_id')

    if not content or not chat_id:
        return jsonify({"error": "Dados incompletos"}), 400

    # Apenas enfileira. O Supabase será chamado pela Thread em background.
    enqueue_message(content, chat_id, current_user_id)

    return jsonify({"message": "Mensagem enviada para processamento"}), 202