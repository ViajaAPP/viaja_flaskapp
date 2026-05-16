from flask import Blueprint, request, jsonify, current_app
from app.services.supabase_service import supabase
from app.utils.auth import token_required

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/instances/<int:tour_instance_id>', methods=['POST'])
@token_required
def init_chat(current_user, tour_instance_id):
    """
    Iniciar um chat para uma instância de tour
    ---
    tags:
        - Chat
    parameters:
        - name: tour_instance_id
          in: path
          type: integer
          required: true
          description: ID da instância de tour para a qual o chat será iniciado
    responses:
        201:
            description: Chat criado com sucesso
        403:
            description: Acesso negado
        404:
            description: Tour não encontrado
        500:
            description: Erro ao criar chat para tour
    """
    # verifica se a instância de tour existe e seleciona o tour_id
    tour_instance_response = supabase.table("tour_instance").select("*").eq("id", tour_instance_id).execute()
    if not tour_instance_response.data:
        return jsonify({"error": "Tour não encontrado"}), 404
    tour_instance = tour_instance_response.data[0]
    tour_id = tour_instance['tour_id']
    
    # verifica se o usuário é criador do tour
    tour_response = supabase.table("tour").select("*").eq("id", tour_id).execute()
    if not tour_response.data:
        return jsonify({"error": "Tour não encontrado"}), 404
    tour = tour_response.data[0]
    if tour['created_by_id'] != current_user['user_id']:
        return jsonify({"error": "Acesso negado"}), 403

    # cria ou recupera o chat para esta instância de tour
    chat_response = supabase.table("chat").select("*").eq("tour_instance_id", tour_instance_id).execute()
    
    if chat_response.data:
        chat = chat_response.data[0]
        return jsonify({"message": "Chat já existe para esta instância de tour", "chat_id": chat['id']}), 200
    
    new_chat = {
        "tour_instance_id": tour_instance_id
    }
    response = supabase.table("chat").insert(new_chat).execute()
    chat_data = response.data
    if not chat_data:
        return jsonify({"error": "Erro ao criar chat para tour"}), 500
    return jsonify({"message": "Chat criado com sucesso!", "chat_id": chat_data[0]['id']}), 201

@chat_bp.route('/', methods=['GET'])
@token_required
def list_chats(current_user):
    pass

@chat_bp.route('/<int:chat_id>/messages', methods=['POST'])
@token_required
def send_message(current_user, chat_id):
    pass

@chat_bp.route('/<int:chat_id>/messages', methods=['GET'])
@token_required
def get_chat_messages(current_user, chat_id):
    pass