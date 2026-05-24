from flask import Blueprint, request, jsonify, current_app
from app.services.supabase_service import supabase
from app.utils.auth import token_required

chat_bp = Blueprint('chat', __name__)

def _get_last_messages(chat_id, limit=20, offset=0):
    """Recupera as últimas mensagens de um chat específico."""
    messages_response = (
        supabase.table("chat_message")
        .select("*")
        .eq("chat_id", chat_id)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return messages_response.data or []

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
    
    # verifica se o usuário é criador do tour!!!
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


def _get_accessible_tour_instance_ids(current_user):
    """IDs de instâncias de tour em que o usuário participa (guia ou turista aceito)."""
    user_id = current_user['user_id']
    role = current_user.get('role')

    if role == "GUIDE":
        tours_response = supabase.table("tour").select("id").eq("created_by_id", user_id).execute()
        tour_ids = [t['id'] for t in (tours_response.data or [])]
        if not tour_ids:
            return []
        instances_response = (
            supabase.table("tour_instance").select("id").in_("tour_id", tour_ids).execute()
        )
        return [i['id'] for i in (instances_response.data or [])]

    if role == "TOURIST":
        requests_response = (
            supabase.table("tour_request")
            .select("tour_instance_id")
            .eq("requester_id", user_id)
            .eq("status", "ACCEPTED")
            .execute()
        )
        return [r['tour_instance_id'] for r in (requests_response.data or [])]

    return None


@chat_bp.route('/', methods=['GET'])
@token_required
def list_chats(current_user): # lista chats do usuário autenticado
    """
    Listar chats do usuário autenticado
    ---
    tags:
        - Chat
    description: |
        Retorna todos os chats em que o usuário participa.
        Guias veem chats das instâncias dos tours que criaram.
        Turistas veem chats das instâncias em que foram aceitos.
        Um usuário pode ter vários chats abertos ao mesmo tempo.
    responses:
        200:
            description: Lista de chats do usuário
        403:
            description: Acesso negado
        500:
            description: Erro ao listar chats
    """
    role = current_user.get('role')
    if role not in ["GUIDE", "TOURIST"]:
        return jsonify({"error": "Acesso negado"}), 403

    try:
        instance_ids = _get_accessible_tour_instance_ids(current_user)
        if instance_ids is None:
            return jsonify({"error": "Acesso negado"}), 403
        if not instance_ids:
            return jsonify([]), 200

        chats_response = (
            supabase.table("chat")
            .select("*, tour_instance(*, tour(id, title, description, meeting_point))")
            .in_("tour_instance_id", instance_ids)
            .execute()
        )
        return jsonify(chats_response.data or []), 200
    except Exception as e:
        current_app.logger.error(f"Erro ao listar chats do usuário: {e}")
        return jsonify({"error": "Erro ao listar chats"}), 500

@chat_bp.route('/<int:chat_id>/messages', methods=['POST'])
@token_required
def send_message(current_user, chat_id):
    pass

@chat_bp.route('/<int:chat_id>/messages', methods=['GET'])
@token_required
def get_chat_messages(current_user, chat_id):
    pass