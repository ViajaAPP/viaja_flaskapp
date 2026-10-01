from flask import Blueprint, request, jsonify, current_app
from app.services.supabase_service import supabase
from app.services import chat_service
from app.utils.auth import token_required
from app.routes.chat_socket import publish

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
    try:
        instance_ids = chat_service.instancias_do_usuario(current_user['user_id'])
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
    """
    Enviar mensagem para um chat específico
    ---
    tags:
        - Chat
    description: |
        Envia uma mensagem para o chat identificado por `chat_id`.
        O usuário deve participar do chat para enviar mensagens.
    parameters:
        - name: chat_id
          in: path
          description: ID do chat
          required: true
          type: integer
        - name: content
          in: body
          description: Conteúdo da mensagem
          required: true
          type: string
    responses:
        201:
            description: Mensagem enviada com sucesso
        400:
            description: ID do chat é obrigatório ou conteúdo da mensagem é obrigatório
        404:
            description: Chat não encontrado
        500:
            description: Erro ao enviar mensagem
    """
    if(chat_id is None):
        return jsonify({"error": "ID do chat é obrigatório"}), 400
    data = request.get_json() or {}
    content = str(data.get("content") or "").strip()
    if not content:
        return jsonify({"error": "Conteúdo da mensagem é obrigatório"}), 400
    
    try:
        chat = chat_service.buscar_chat(chat_id)
        if not chat:
            return jsonify({"error": "Chat não encontrado"}), 404
        if not chat_service.participa(current_user['user_id'], chat):
            return jsonify({"error": "Você não participa dessa conversa"}), 403

        mensagem = chat_service.salvar_mensagem(chat_id, current_user['user_id'], content)
        publish(chat_id, {"type": "message", **mensagem}, exceto_user_id=current_user['user_id'])
        return jsonify(mensagem), 201
    except Exception as e:
        current_app.logger.error(f"Erro ao enviar mensagem: {e}")
        return jsonify({"error": "Erro ao enviar mensagem"}), 500

@chat_bp.route('/<int:chat_id>/messages', methods=['GET'])
@token_required
def get_chat_messages(current_user, chat_id):
    chat = chat_service.buscar_chat(chat_id)
    if not chat:
        return jsonify({"error": "Chat não encontrado"}), 404
    if not chat_service.participa(current_user['user_id'], chat):
        return jsonify({"error": "Você não participa dessa conversa"}), 403
    limite = min(request.args.get('limit', 20, type=int), 100)
    inicio = max(request.args.get('offset', 0, type=int), 0)
    return jsonify(chat_service.ultimas_mensagens(chat_id, limite, inicio)), 200