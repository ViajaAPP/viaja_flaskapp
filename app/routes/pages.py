from flask import Blueprint, current_app, request, jsonify
from app.services.supabase_service import supabase
from app.utils.auth import token_required
from app.routes.chat import _get_last_messages
from app.routes.socket import _get_websocket_url
from datetime import timedelta, datetime, timezone

pages_bp = Blueprint('pages', __name__)

@pages_bp.route('/home', methods=['POST'])
@token_required
def home(current_user):
    """
    Página inicial do aplicativo
    ---
    tags:
        - Pages
    parameters:
        - name: current_user
          in: header
          type: string
          required: true
          description: Token de autenticação do usuário
    responses:
        200:
            type: object
            properties:
                message:
                    type: string
            description: Mensagem de boas-vindas personalizada para o usuário
            schema:
                type: object
                properties:
                    message:
                        type: string
        401:
            description: Token de autenticação inválido ou ausente
        500:
            description: Erro ao acessar a página inicial
    """
    try:
        # buscar usuário no banco de dados usando o ID do token
        user_response = supabase.table("user").select("first_name, last_name, photo").eq("user_id", current_user['user_id']).execute()
        if not user_response.data:
            return jsonify({"error": "Usuário não encontrado"}), 404
        user = user_response.data[0]
        
        # buscar popular activities para mostrar na página inicial
        # parametro: 20 tours que tiveram mais membros integrando no total
        tours_response = supabase.rpc("get_popular_tours").execute()
        popular_tours = []
        if tours_response.data:
            for tour in tours_response.data:
                popular_tours.append({
                    "id": tour['id'],
                    "title": tour['title'],
                    "guideFoto": tour['guidephoto'],
                    "guide": tour['guide'],
                    "imageUrl": tour['photo'],
                    "rating": 5,
                    "reviewCount": tour['qt_turistas'],
                    "tag": "Passeio recomendado",
                    "tagType": "recommended"
                })
        
        return jsonify({
            "user": {
                "name": user['first_name'],
                "fotoUser": user['photo']
            },
            "greeting": 'Bem-vindo de volta,',
            "titulo": 'Para onde vamos hoje?',
            "categories": [
                { "id": "all", "label": "todos", "active": True },
                { "id": "most-liked", "label": "mais curtidos", "active": False },
                { "id": "most-searched", "label": "mais procurados", "active": False },
                { "id": "nearby", "label": "mais perto", "active": False }
            ],
            "popularActivities": popular_tours
        }), 200
    except Exception as e:
        current_app.logger.error(f"Erro ao acessar a página inicial: {str(e)}")
        return jsonify({"error": "Erro ao acessar a página inicial"}), 500
    
@pages_bp.route('/chats', methods=['POST'])
@token_required
def chats(current_user):
    """
    Página de chats do aplicativo
    ---
    tags:
        - Pages
    parameters:
        - name: current_user
          in: header
          type: string
          required: true
          description: Token de autenticação do usuário
    responses:
        200:
            type: object
            properties:
                message:
                    type: string
            description: Eventos em que a pessoa está participando ou organizando
            schema:
                type: object
                properties:
                    message:
                        type: string
        401:
            description: Token de autenticação inválido ou ausente
        500:
            description: Erro ao acessar a página de chats
    """
    try:
        tour_list = []
        if current_user['role'] == 'GUIDE':
            # busca os tours dele que tem mais de uma pessoa participando
            tours_response = supabase.rpc("get_tours_guide", {"guide_id": current_user['user_id']}).execute()
        if current_user['role'] == 'TOURIST':
            # busca os tours que ele está participando
            tours_response = supabase.rpc("get_tours_tourist", {"tourist_id": current_user['user_id']}).execute()

        for tour in tours_response.data:
            tour_date = ''
            current_time = datetime.now(timezone.utc)
            
            start_time_str = tour['start_time'].replace('Z', '+00:00')
            tour_start_time = datetime.fromisoformat(start_time_str)
            
            if tour_start_time <= current_time:
                tour_date = 'Evento em andamento'
            elif tour_start_time.date() == current_time.date():
                tour_date = 'Saída hoje às ' + tour_start_time.strftime('%H:%M')
            elif tour_start_time.date() == (current_time + timedelta(days=1)).date():
                tour_date = 'Saída amanhã às ' + tour_start_time.strftime('%H:%M')
            else:
                tour_date = 'Saída em ' + tour_start_time.strftime('%d/%m/%Y, %H:%M')
                
            members = supabase.rpc("get_tour_members", {"tour_instance_id": tour['tour_instance_id']}).execute()
                
            tour_list.append({
                "tour_id": tour['tour_id'],
                "tour_instance_id": tour['tour_instance_id'],
                "tour_title": tour['tour_title'],
                "tour_photo": tour['tour_photo'],
                "tour_date": tour_date,
                "chat_id": tour['chat_id'],
                "chat_open": tour['chat_id'] is not None,
                "members": members.data if members.data else []
            })
            
        return jsonify({
            "tour_list": tour_list,
            "direct_conversations": []
        }), 200
    except Exception as e:
        current_app.logger.error(f"Erro ao acessar a página de chats: {str(e)}")
        return jsonify({"error": "Erro ao acessar a página de chats"}), 500
    
@pages_bp.route('/chat', methods=['POST'])
@token_required
def chat(current_user):
    """
    Página de um chat específico do aplicativo
    ---
    tags:
        - Pages
    parameters:
        - name: current_user
          in: header
          type: string
          required: true
          description: Token de autenticação do usuário
        - name: chat_id
          in: body
          type: integer
          required: true
          description: ID do chat a ser acessado
    responses:
        200:
            type: object
            properties:
                message:
                    type: string
            description: Detalhes do chat, incluindo mensagens e participantes
            schema:
                type: object
                properties:
                    message:
                        type: string
    """
    chat_id = request.json.get('chat_id')
    if not chat_id:
        return jsonify({"error": "ID do chat é obrigatório"}), 400
    try:
        chat_name = ''
        chat_response = supabase.rpc('get_tour_by_chat', {"chat_id": chat_id}).execute()
        if chat_response.data:
            chat_name = chat_response.data[0]['tour_title']
            
        members_response = supabase.rpc('get_tour_members', {"tour_instance_id": chat_response.data[0]['tour_instance_id']}).execute()
        user_list = []
        if members_response.data:
            for member in members_response.data:
                user_list.append({
                    "user_id": member['user_id'],
                    "first_name": member['first_name'],
                    "last_name": member['last_name'],
                    "photo": member['photo']
                })
        
        messages_list = _get_last_messages(chat_id)
        socket_connection_url = _get_websocket_url()
        print("URL do WebSocket:", socket_connection_url)  # Log para verificar a URL do WebSocket
        if not socket_connection_url:
            return jsonify({"error": "URL do WebSocket não encontrada"}), 500
        
        socket_connection_url = socket_connection_url + f"ws?user_id={current_user['user_id']}&chats={chat_id}"
        
        return jsonify({
            "chat_name": chat_name,
            "user_list": user_list,
            "messages_list": messages_list,
            "socket_connection_url": socket_connection_url
        }), 200
    except Exception as e:
        current_app.logger.error(f"Erro ao acessar a página do chat: {str(e)}")
        return jsonify({"error": "Erro ao acessar a página do chat"}), 500