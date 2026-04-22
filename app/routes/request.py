from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timezone
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
    
@request_bp.route('/', methods=['GET'])
@token_required
def list_user_requests(current_user):
    """
    Listar solicitações do usuário
    ---
    tags:
        - Tour Requests
    security:
        - bearerAuth: []
    responses:
        200:
            description: Lista de solicitações do usuário
        403:
            description: Acesso negado: usuário não autorizado para visualizar solicitações
        500:
            description: Erro ao listar solicitações do usuário
    """
    # role do current_user deve ser TOURIST ou GUIDE
    role = current_user.get('role')
    if role not in ["TOURIST"]:
        return jsonify({"error": "Acesso negado: usuário não autorizado para visualizar solicitações"}), 403
    
    try:
        # buscar informações da request, do tour instance e do tour para cada request do usuário
        requests_response = supabase.table("tour_request").select("*, tour_instance(*, tour(*))").eq("requester_id", current_user['user_id']).execute()
        requests = requests_response.data
        return jsonify(requests), 200
    except Exception as e:
        current_app.logger.error(f"Exceção ao listar solicitações do usuário: {str(e)}")
        return jsonify({"error": "Erro ao listar solicitações do usuário"}), 500

@request_bp.route('/instances/<int:tour_instance_id>', methods=['GET'])
@token_required
def list_tour_requests(current_user, tour_instance_id):
    # Donos da tour podem ver solicitações de todos os status (e com filtro também), enquanto turistas só podem ver suas próprias solicitações e as de quem já foi aceito.
    """
    Listar solicitações para uma instância de tour
    ---
    tags:
        - Tour Requests
    parameters:
        - in: path
            name: tour_instance_id
            required: true
            schema:
                type: integer
            description: ID da instância de tour para a qual as solicitações estão sendo listadas.
        - in: query
            name: status
            required: false
            schema:
                type: string
                enum: [PENDING, ACCEPTED, DENIED]
            description: Filtro opcional para listar solicitações por status.
    security:
        - bearerAuth: []
    responses:
        200:
            description: Lista de solicitações para a instância de tour.
        404:
            description: Tour não encontrado
        403:
            description: Acesso negado: usuário não autorizado para visualizar solicitações
        500:
            description: Erro ao listar solicitações para tour
    """
    # role do current_user deve ser TOURIST ou GUIDE
    role = current_user.get('role')
    if role not in ["TOURIST", "GUIDE"]:
        return jsonify({"error": "Acesso negado: usuário não autorizado para visualizar solicitações"}), 403
    
    status = request.args.get('status', None)
    # verifica se a instância de tour existe
    tour_instance_response = supabase.table("tour_instance").select("*").eq("id", tour_instance_id).execute()
    if not tour_instance_response.data:
        return jsonify({"error": "Tour não encontrado"}), 404
    
    tour_instance = tour_instance_response.data[0]
    # turistas só podem ver suas próprias solicitações e as de quem já foi aceito, enquanto guias podem ver todas as solicitações
    if role == "TOURIST":
        requests_response = supabase.table("tour_request").select("*").eq("tour_instance_id", tour_instance_id).eq("requester_id", current_user['user_id']).execute()
        accepted_requests_response = supabase.table("tour_request").select("*").eq("tour_instance_id", tour_instance_id).eq("status", "ACCEPTED").execute()
        requests = requests_response.data + accepted_requests_response.data
    else:
        requests_response = supabase.table("tour_request").select("*, tour_instance(*, tour(*))").eq("tour_instance_id", tour_instance_id).execute()
        requests = requests_response.data
        if status:
            requests = [r for r in requests if r['status'] == status]
    return jsonify(requests), 200
    
@request_bp.route('/<int:request_id>', methods=['PATCH'])
@token_required
def update_tour_request_status(current_user, request_id):
    """
    Atualizar o status de um tour request (aceitar ou recusar)
    ---
    tags:
        - Tour Requests
    parameters:
        - in: path
            name: request_id
            required: true
            schema:
                type: integer
            description: ID do tour request a ser atualizado
    requestBody:
        required: true
        content:
            application/json:
                schema:
                    type: object
                    properties:
                        status:
                            type: string
                            enum: [ACCEPTED, DENIED]
                            description: Novo status para o tour request
    security:
        - bearerAuth: []
    responses:
        200:
            description: Status do tour request atualizado com sucesso
        400:
            description: Dados de atualização ausentes ou inválidos
        404:
            description: Tour request, tour instance ou tour não encontrado
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            error:
                                type: string
                    examples:
                        request_nao_encontrado:
                            summary: Tour request não encontrado
                            value: {"error": "Tour request não encontrado"}
                        tour_instance_nao_encontrada:
                            summary: Tour instance não encontrada
                            value: {"error": "Tour instance não encontrada"}
                        tour_nao_encontrado:
                            summary: Tour não encontrado
                            value: {"error": "Tour não encontrado"}

        403:
            description: Acesso negado: usuário não autorizado para atualizar status
        409:
            description: Conflito de negócio (Capacidade)
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
        500:
            description: Erro ao atualizar status do tour request
    """
    tour_request_response = supabase.table("tour_request").select("*").eq("id", request_id).execute()
    if not tour_request_response.data:
        return jsonify({"error": "Tour request não encontrado"}), 404
    
    tour_instance_response = supabase.table("tour_instance").select("*").eq("id", tour_request_response.data[0]['tour_instance_id']).execute()
    if not tour_instance_response.data:
        return jsonify({"error": "Tour instance não encontrada"}), 404
    
    tour_response = supabase.table("tour").select("*").eq("id", tour_instance_response.data[0]['tour_id']).execute()
    if not tour_response.data:
        return jsonify({"error": "Tour não encontrado"}), 404
    
    tour = tour_response.data[0]
    if tour['created_by_id'] != current_user['user_id']:
        return jsonify({"error": "Acesso negado: usuário não autorizado para atualizar status"}), 403
    
    # recupera novo status do body da requisição
    data = request.get_json()
    if not data or 'status' not in data:
        return jsonify({"error": "Dados de atualização ausentes ou inválidos"}), 400
    
    new_status = data['status']
    if new_status not in ["ACCEPTED", "DENIED"]:
        return jsonify({"error": "Dados de atualização ausentes ou inválidos"}), 400
    
    if new_status == "ACCEPTED":
        # consulta quantas pessoas estão com solicitações aprovadas para esta instância de tour
        approved_requests_count_response = supabase.table("tour_request").select("id", count="exact").eq("tour_instance_id", tour_instance_response.data[0]['id']).eq("status", "ACCEPTED").execute()
        approved_requests_count = approved_requests_count_response.count
        if approved_requests_count and approved_requests_count >= tour_instance_response.data[0]['max_capacity']:
            return jsonify({"error": "O tour está preenchido"}), 409

    try:
        supabase.table("tour_request").update({"status": new_status, "last_update": datetime.now(timezone.utc).isoformat()}).eq("id", request_id).execute()
        return jsonify({"message": "Status do tour request atualizado com sucesso!"}), 200
    except Exception as e:
        current_app.logger.error(f"Exceção ao atualizar status do tour request: {str(e)}")
        return jsonify({"error": "Erro ao atualizar status do tour request"}), 500