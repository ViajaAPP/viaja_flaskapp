from flask import Blueprint, current_app, request, jsonify
from app.services.supabase_service import supabase
from app.utils.auth import token_required

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