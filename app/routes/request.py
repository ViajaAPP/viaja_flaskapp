from flask import Blueprint, request, jsonify, current_app
from app.services.supabase_service import supabase
from app.models.request_models import TourRequestCreateModel
from app.utils.auth import token_required

request_bp = Blueprint('request', __name__)

@request_bp.route('/instances/<int:tour_instance_id>', methods=['POST'])
@token_required
def create_tour_request(current_user, tour_instance_id):
    """
    Criar um novo tour request
    ---
    tags:
        - Tour Requests
    parameters:
        - in: path
            name: tour_instance_id
            required: true
            schema:
                type: integer
            description: ID da instância de tour para a qual o request está sendo criado
    requestBody:
        required: true
        content:
            application/json:
                schema:
                    type: object
                    properties:
                        message:
                            type: string
                            description: Mensagem opcional do viajante para o guia
    security:
        - bearerAuth: []
    responses:
        201:
            description: Solicitação para tour criado com sucesso
        400:
            description: Dados da solicitação para tour ausentes ou inválidos
        404:
            description: Tour não encontrado
        403:
            description: Acesso negado: usuário não autorizado para criar solicitações
        409:
            description: Conflito de negócio (Capacidade ou Disponibilidade)
            content:
            application/json:
                schema:
                type: object
                properties:
                    error:
                    type: string
                examples:
                    lotado:
                        summary: Tour lotado
                        value: {"error": "O tour está preenchido"}
                    indisponivel:
                        summary: Tour desativado
                        value: {"error": "O tour não está disponível para solicitações"}
                    solicitado:
                        summary: Viajante já solicitou este tour
                        value: {"error": "Você já tem uma solicitação para este tour"}
        500:
            description: Erro ao criar solicitação para tour
    """
    # role do current_user deve ser TRAVELER
    role = current_user.get('role')
    if role != "TOURIST":
        return jsonify({"error": "Acesso negado: usuário não autorizado para criar solicitações"}), 403
    
    # recupera dados do tour request
    data = request.get_json()
    if not data:
        return jsonify({"error": "Dados da solicitação para tour ausentes ou inválidos"}), 400
    
    # verifica se a instância de tour existe e está disponível para solicitações
    tour_instance_response = supabase.table("tour_instance").select("*").eq("id", tour_instance_id).execute()
    if not tour_instance_response.data:
        return jsonify({"error": "Tour não encontrado"}), 404
    
    tour_instance = tour_instance_response.data[0]
    
    if tour_instance['status'] != "SCHEDULED":
        return jsonify({"error": "O tour não está disponível para solicitações"}), 409

    # consulta quantas pessoas estão com solicitações aprovadas para esta instância de tour
    approved_requests_response = supabase.table("tour_request").select("*").eq("tour_instance_id", tour_instance_id).eq("status", "ACCEPTED").execute()
    approved_requests = approved_requests_response.data
    if approved_requests and len(approved_requests) >= tour_instance['max_capacity']:
        return jsonify({"error": "O tour está preenchido"}), 409
    
    # verifica se o viajante já tem uma solicitação para esta instância de tour
    existing_request_response = supabase.table("tour_request").select("*").eq("tour_instance_id", tour_instance_id).eq("requester_id", current_user['user_id']).execute()
    if existing_request_response.data:
        return jsonify({"error": "Você já tem uma solicitação para este tour"}), 409
    
    # cria o tour request
    tour_request = TourRequestCreateModel(
        requester_id=current_user['user_id'],
        tour_instance_id=tour_instance_id,
        message=data.get('message', '')
    )
    try:
        response = supabase.table("tour_request").insert(tour_request.dict()).execute()
        request_data = response.data
        if not request_data:
            return jsonify({"error": "Erro ao criar solicitação para tour"}), 500
        return jsonify({"message": "Solicitação para tour criada com sucesso!", "request_id": request_data[0]['id']}), 201
    except Exception as e:
        current_app.logger.error(f"Exceção ao criar solicitação para tour: {str(e)}")
        return jsonify({"error": "Erro ao criar solicitação para tour"}), 500