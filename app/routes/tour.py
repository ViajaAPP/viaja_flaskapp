from flask import Blueprint, request, jsonify, current_app
from app.services.supabase_service import supabase
from app.models.tour_models import TourCreateModel, TourInstanceCreateModel
from app.utils.auth import token_required

tour_bp = Blueprint('tour', __name__)

@tour_bp.route('/', methods=['POST'])
@token_required
def create_tour(current_user):
    """
    Criar um novo tour
    ---
    tags:
        - Tours
    security:
        - BearerAuth: []
    requestBody:
        required: true
        content:
            application/json:
                schema:
                    type: object
                    properties:
                        title:
                            type: string
                        description:
                            type: string
                        price:
                            type: number
                        estimated_duration_minutes:
                            type: integer
                        meeting_point:
                            type: string
    responses:
        201:
            description: Tour criado com sucesso
        400:
            description: Dados do tour ausentes ou inválidos
        500:
            description: Erro ao criar tour
    """
    # role do current_user deve ser GUIDE
    role = current_user.get('role')
    if role != "GUIDE":
        return jsonify({"error": "Acesso negado: apenas guias podem criar tours"}), 403
    
    # recupera dados do tour
    data = request.get_json()
    if not data:
        return jsonify({"error": "Dados do tour não fornecidos!"}), 400
    
    if not all([data.get('title'), data.get('price'), data.get('estimated_duration_minutes'), data.get('meeting_point')]):
        return jsonify({"error": "Campos obrigatórios faltando! Campos: title, price, estimated_duration_minutes, meeting_point"}), 400
    
    try:
        tour = TourCreateModel(
            created_by_id=current_user['user_id'],
            title=data.get('title'),
            description=data.get('description'),
            price=data.get('price'),
            estimated_duration_minutes=data.get('estimated_duration_minutes'),
            meeting_point=data.get('meeting_point')
        )
        supabase.table("tour").insert(tour.dict()).execute()
        return jsonify({"message": "Tour criado com sucesso!"}), 201

    except Exception as e:
        return jsonify({"error": f"Erro ao criar tour: {e}"}), 500

@tour_bp.route('/<int:tour_id>/instance', methods=['POST'])
@token_required
def create_tour_instance(current_user, tour_id):
    """
    Criar uma nova instância de tour
    ---
    tags:
        - Tours
    security:
        - BearerAuth: []
    parameters:
        - in: path
            name: tour_id
            required: true
            schema:
                type: integer
    requestBody:
        required: true
        content:
            application/json:
                schema:
                    type: object
                    properties:
                        start_time:
                            type: string
                            format: date-time
                        max_capacity:
                            type: integer
    responses:
        201:
            description: Instância de tour criada com sucesso
        400:
            description: Dados da instância de tour ausentes ou inválidos
        403:
            description: Acesso negado: usuário não autorizado para criar instâncias de tours
        404:
            description: Tour não encontrado
        500:
            description: Erro ao criar instância de tour
    """
    # role do current_user deve ser GUIDE
    role = current_user.get('role')
    if role != "GUIDE":
        return jsonify({"error": "Acesso negado: apenas guias podem criar instâncias de tours"}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "Dados da instância de tour não fornecidos!"}), 400
    
    if not all([data.get('start_time'), data.get('max_capacity')]):
        return jsonify({"error": "Campos obrigatórios faltando! Campos: start_time, max_capacity"}), 400
    
    # verificar se o tour é do guia logado
    try:
        tour_response = supabase.table("tour").select("*").eq("id", tour_id).execute()
        tour_data = tour_response.data
        if not tour_data:
            return jsonify({"error": "Tour não encontrado!"}), 404
        tour = tour_data[0]
        if tour['created_by_id'] != current_user['user_id']:
            return jsonify({"error": "Acesso negado: você só pode criar instâncias para seus próprios tours"}), 403
    except Exception as e:
        return jsonify({"error": f"Erro ao verificar tour: {e}"}), 500
    
    try:
        tour_instance = TourInstanceCreateModel(
            tour_id=tour_id,
            start_time=data.get('start_time'),
            max_capacity=data.get('max_capacity')
        )
        supabase.table("tour_instance").insert(tour_instance.model_dump(mode='json')).execute()
        return jsonify({"message": "Instância de tour criada com sucesso!"}), 201

    except Exception as e:
        return jsonify({"error": f"Erro ao criar instância de tour: {e}"}), 500