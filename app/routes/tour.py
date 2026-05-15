from flask import Blueprint, request, jsonify, current_app
from app.services.supabase_service import supabase
from app.models.tour_models import TourCreateModel, TourInstanceCreateModel
from app.models.address_models import AddressCreateModel
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
    parameters:
        - in: body
          name: tour
          description: Dados do tour a ser criado
          required: true
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
                    cep:
                        type: string
                    uf:
                        type: string
                    city:
                        type: string
                    neighborhood:
                        type: string
                    number:
                        type: string
    responses:
        201:
            description: Tour criado com sucesso
            schema:
                type: object
                properties:
                    message:
                        type: string
                    tour_id:
                        type: integer
        400:
            description: Dados do tour não fornecidos ou campos obrigatórios faltando
            schema:
                type: object
                properties:
                    error:
                        type: string
        403:
            description: Acesso negado
            schema:
                type: object
                properties:
                    error:
                        type: string
        500:
            description: Erro ao criar tour
            schema:
                type: object
                properties:
                    error:
                        type: string
    """
    # role do current_user deve ser GUIDE
    role = current_user.get('role')
    if role != "GUIDE":
        return jsonify({"error": "Acesso negado"}), 403
    
    # recupera dados do tour
    data = request.get_json()
    if not data:
        return jsonify({"error": "Dados do tour não fornecidos"}), 400
    
    campos_obrigatorios = ['title', 'description', 'price', 'estimated_duration_minutes', 'meeting_point', 'cep', 'uf', 'city', 'neighborhood', 'number']
    campos_faltando = [campo for campo in campos_obrigatorios if not data.get(campo)]
    if campos_faltando:
        return jsonify({"error": f"Campos obrigatórios faltando! Campos: {', '.join(campos_faltando)}"}), 400
    
    address = AddressCreateModel(
        cep=data.get('cep'),
        uf=data.get('uf'),
        city=data.get('city'),
        neighborhood=data.get('neighborhood'),
        street=data.get('street'),
        number=data.get('number')
    )
    
    # procura se já existe um endereço com o mesmo CEP, UF, cidade, bairro, rua e número no banco, se existir, usa o id desse endereço, se não, cria um novo endereço e usa o id do novo endereço
    address_id = None
    address_response = supabase.table("address").select("id").eq("cep", address.cep).eq("neighborhood", address.neighborhood).eq("street", address.street).eq("number", address.number).execute()
    address_data = address_response.data
    if address_data:
        address_id = address_data[0]['id']
    else:
        address_insert_response = supabase.table("address").insert(address.dict()).execute()
        address_insert_data = address_insert_response.data
        if not address_insert_data:
            return jsonify({"error": "Erro ao criar endereço"}), 500
        address_id = address_insert_data[0]['id']
    
    try:
        tour = TourCreateModel(
            created_by_id=current_user['user_id'],
            title=data.get('title'),
            description=data.get('description'),
            price=data.get('price'),
            estimated_duration_minutes=data.get('estimated_duration_minutes'),
            meeting_point=data.get('meeting_point'),
            address_id=address_id
        )
        response = supabase.table("tour").insert(tour.dict()).execute()
        tour_data = response.data
        if not tour_data:
            return jsonify({"error": "Erro ao criar tour"}), 500
        return jsonify({"message": "Tour criado com sucesso", "tour_id": tour_data[0]['id']}), 201

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
    parameters:
        - in: path
          name: tour_id
          description: ID do tour para o qual a instância será criada
          required: true
          type: integer
        - in: body
          name: tour_instance
          description: Dados da instância de tour a ser criada
          required: true
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
            schema:
                type: object
                properties:
                    message:
                        type: string
                    instance_id:
                        type: integer
        400:
            description: Dados da instância de tour não fornecidos ou campos obrigatórios faltando
            schema:
                type: object
                properties:
                    error:
                        type: string
        403:
            description: Acesso negado
            schema:
                type: object
                properties:
                    error:
                        type: string
        404:
            description: Tour não encontrado
            schema:
                type: object
                properties:
                    error:
                        type: string
        500:
            description: Erro ao criar instância de tour
            schema:
                type: object
                properties:
                    error:
                        type: string
    """
    # role do current_user deve ser GUIDE
    role = current_user.get('role')
    if role != "GUIDE":
        return jsonify({"error": "Acesso negado"}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "Dados da instância de tour não fornecidos"}), 400
    
    if not all([data.get('start_time'), data.get('max_capacity')]):
        return jsonify({"error": "Campos obrigatórios faltando! Campos: start_time, max_capacity"}), 400
    
    # verificar se o tour é do guia logado
    try:
        tour_response = supabase.table("tour").select("*").eq("id", tour_id).execute()
        tour_data = tour_response.data
        if not tour_data:
            return jsonify({"error": "Tour não encontrado"}), 404
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
        response = supabase.table("tour_instance").insert(tour_instance.model_dump(mode='json')).execute()
        instance_data = response.data
        if not instance_data:
            return jsonify({"error": "Erro ao criar instância de tour"}), 500
        return jsonify({"message": "Instância de tour criada com sucesso", "instance_id": instance_data[0]['id']}), 201

    except Exception as e:
        return jsonify({"error": f"Erro ao criar instância de tour: {e}"}), 500