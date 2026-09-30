from flask import Blueprint, request, jsonify, current_app
from pydantic import ValidationError
from app.services.supabase_service import supabase
from app.services import tour_service, cidades_service, foto_service
from app.models.enums import UserRole, RegistrationStatus, RequestStatus
from app.models.tour_models import TourCreateModel, TourUpdateModel, TourInstanceCreateModel, TourInstanceUpdateModel
from app.models.address_models import AddressCreateModel
from app.utils.auth import token_required, role_required, is_tour_owner, can_moderate_tour

tour_bp = Blueprint('tour', __name__)

ADDRESS_FIELDS = ['cep', 'uf', 'city', 'neighborhood', 'street', 'number']
TOUR_REQUIRED_FIELDS = ['title', 'description', 'price', 'estimated_duration_minutes', 'meeting_point', 'photo'] + ADDRESS_FIELDS
TOUR_EDITABLE_FIELDS = ['title', 'description', 'price', 'estimated_duration_minutes', 'meeting_point', 'photo']

def _missing_fields(data, fields):
    return [field for field in fields if not data.get(field)]

def _address_from(data):
    return AddressCreateModel(**{field: data.get(field) for field in ADDRESS_FIELDS})

def _serialize_instance(instance, request_status_by_instance):
    return {
        **instance,
        "current_capacity": tour_service.count_accepted_requests(instance['id']),
        "my_request_status": request_status_by_instance.get(instance['id']),
        "open_for_requests": tour_service.is_instance_open_for_requests(instance)
    }

def _is_on_tour(tour, instance_id, current_user):
    if is_tour_owner(tour, current_user):
        return True
    participation_response = supabase.table("tour_request").select("id").eq("tour_instance_id", instance_id).eq("requester_id", current_user['user_id']).eq("status", RequestStatus.ACCEPTED.value).execute()
    return bool(participation_response.data)

@tour_bp.route('/', methods=['POST'])
@token_required
@role_required(UserRole.GUIDE)
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
                    photo:
                        type: string
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
                    street:
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
    data = request.get_json()
    if not data:
        return jsonify({"error": "Dados do tour não fornecidos"}), 400

    campos_faltando = _missing_fields(data, TOUR_REQUIRED_FIELDS)
    if campos_faltando:
        return jsonify({"error": f"Campos obrigatórios faltando! Campos: {', '.join(campos_faltando)}"}), 400

    try:
        address_id = tour_service.find_or_create_address(_address_from(data))
        if not address_id:
            return jsonify({"error": "Erro ao criar endereço"}), 500
        tour = TourCreateModel(
            created_by_id=current_user['user_id'],
            title=data.get('title'),
            description=data.get('description'),
            price=data.get('price'),
            estimated_duration_minutes=data.get('estimated_duration_minutes'),
            meeting_point=data.get('meeting_point'),
            photo=data.get('photo'),
            address_id=address_id
        )
    except ValidationError as e:
        return jsonify({"error": f"Dados do tour inválidos: {e}"}), 400

    try:
        response = supabase.table("tour").insert(tour.model_dump()).execute()
        tour_data = response.data
        if not tour_data:
            return jsonify({"error": "Erro ao criar tour"}), 500
        return jsonify({"message": "Tour criado com sucesso", "tour_id": tour_data[0]['id']}), 201

    except Exception as e:
        return jsonify({"error": f"Erro ao criar tour: {e}"}), 500

@tour_bp.route('/mine', methods=['GET'])
@token_required
@role_required(UserRole.GUIDE, UserRole.ADMIN)
def list_managed_tours(current_user):
    created_by_id = None if current_user['role'] == UserRole.ADMIN else current_user['user_id']
    try:
        return jsonify(tour_service.list_tours(created_by_id)), 200
    except Exception as e:
        current_app.logger.error(f"Erro ao listar tours: {e}")
        return jsonify({"error": "Erro ao listar tours"}), 500

def _texto_da_distancia(km):
    if km < 1:
        return "A menos de 1 km de você"
    return f"A {round(km)} km de você"

@tour_bp.route('/perto', methods=['GET'])
@token_required
def list_nearby_tours(current_user):
    try:
        origem = (float(request.args['lat']), float(request.args['lon']))
    except (KeyError, ValueError):
        return jsonify({"error": "Informe lat e lon válidos"}), 400

    try:
        tours = tour_service.list_published_tours_with_address()
        guias = tour_service.find_users({tour['created_by_id'] for tour in tours})
        favorite_tour_ids = tour_service.list_favorite_tour_ids(current_user['user_id'])
        proximos = []
        for tour in tours:
            endereco = tour.get('address') or {}
            destino = cidades_service.coordenadas_da_cidade(endereco.get('city'), endereco.get('uf'))
            if not destino:
                continue
            km = cidades_service.distancia_km(origem, destino)
            guia = guias.get(tour['created_by_id']) or {}
            proximos.append({
                "id": tour['id'],
                "title": tour['title'],
                "guideFoto": guia.get('photo'),
                "guide": f"{guia.get('first_name', '')} {guia.get('last_name', '')}".strip(),
                "imageUrl": tour['photo'],
                "rating": 5,
                "reviewCount": 0,
                "tag": _texto_da_distancia(km),
                "tagType": "nearby",
                "favorite": tour['id'] in favorite_tour_ids,
                "distance_km": round(km, 1),
                "city": endereco.get('city'),
                "uf": endereco.get('uf')
            })
        proximos.sort(key=lambda item: item['distance_km'])
        return jsonify(proximos), 200
    except Exception as e:
        current_app.logger.error(f"Erro ao listar tours por perto: {e}")
        return jsonify({"error": "Erro ao listar tours por perto"}), 500

@tour_bp.route('/photo', methods=['POST'])
@token_required
@role_required(UserRole.GUIDE)
def upload_tour_photo(current_user):
    arquivo = request.files.get('photo')
    if not arquivo:
        return jsonify({"error": "Escolha uma foto"}), 400
    try:
        return jsonify({"photo": foto_service.enviar_capa_de_passeio(arquivo, current_user['user_id'])}), 200
    except foto_service.FotoInvalida as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Erro ao enviar capa do passeio: {e}")
        return jsonify({"error": "Erro ao enviar capa do passeio"}), 500

@tour_bp.route('/<int:tour_id>', methods=['GET'])
@token_required
def get_tour(current_user, tour_id):
    try:
        tour = tour_service.find_tour(tour_id)
        if not tour or not (tour['published'] or can_moderate_tour(tour, current_user)):
            return jsonify({"error": "Tour não encontrado"}), 404

        instances = tour_service.list_tour_instances(tour_id)
        request_status_by_instance = tour_service.map_request_status_by_instance(
            current_user['user_id'], [instance['id'] for instance in instances]
        )
        guide = tour_service.find_users([tour['created_by_id']]).get(tour['created_by_id'])
        return jsonify({
            **tour,
            "address": tour_service.find_address(tour['address_id']),
            "guide": guide,
            "instances": [_serialize_instance(instance, request_status_by_instance) for instance in instances],
            "is_owner": is_tour_owner(tour, current_user),
            "can_moderate": can_moderate_tour(tour, current_user),
            "favorite": tour_id in tour_service.list_favorite_tour_ids(current_user['user_id'])
        }), 200
    except Exception as e:
        current_app.logger.error(f"Erro ao obter tour: {e}")
        return jsonify({"error": "Erro ao obter tour"}), 500

@tour_bp.route('/<int:tour_id>', methods=['PATCH'])
@token_required
@role_required(UserRole.GUIDE)
def update_tour(current_user, tour_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Dados do tour não fornecidos"}), 400

    tour = tour_service.find_tour(tour_id)
    if not tour:
        return jsonify({"error": "Tour não encontrado"}), 404
    if not is_tour_owner(tour, current_user):
        return jsonify({"error": "Acesso negado"}), 403

    try:
        changes = {field: data[field] for field in TOUR_EDITABLE_FIELDS if field in data}
        if any(field in data for field in ADDRESS_FIELDS):
            campos_faltando = _missing_fields(data, ADDRESS_FIELDS)
            if campos_faltando:
                return jsonify({"error": f"Campos obrigatórios faltando! Campos: {', '.join(campos_faltando)}"}), 400
            changes['address_id'] = tour_service.find_or_create_address(_address_from(data))
        update = TourUpdateModel(**changes).model_dump(exclude_none=True)
    except ValidationError as e:
        return jsonify({"error": f"Dados do tour inválidos: {e}"}), 400

    try:
        supabase.table("tour").update(update).eq("id", tour_id).execute()
        return jsonify({"message": "Tour atualizado com sucesso"}), 200
    except Exception as e:
        current_app.logger.error(f"Erro ao atualizar tour: {e}")
        return jsonify({"error": "Erro ao atualizar tour"}), 500

@tour_bp.route('/<int:tour_id>/publish', methods=['PATCH'])
@token_required
@role_required(UserRole.GUIDE, UserRole.ADMIN)
def set_tour_published(current_user, tour_id):
    data = request.get_json()
    if not data or not isinstance(data.get('published'), bool):
        return jsonify({"error": "Campo obrigatório faltando! Campos: published"}), 400

    tour = tour_service.find_tour(tour_id)
    if not tour:
        return jsonify({"error": "Tour não encontrado"}), 404
    if not can_moderate_tour(tour, current_user):
        return jsonify({"error": "Acesso negado"}), 403

    try:
        supabase.table("tour").update({"published": data['published']}).eq("id", tour_id).execute()
        return jsonify({"message": "Publicação do tour atualizada", "published": data['published']}), 200
    except Exception as e:
        current_app.logger.error(f"Erro ao publicar tour: {e}")
        return jsonify({"error": "Erro ao publicar tour"}), 500

@tour_bp.route('/<int:tour_id>/instance', methods=['POST'])
@token_required
@role_required(UserRole.GUIDE)
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
    data = request.get_json()
    if not data:
        return jsonify({"error": "Dados da instância de tour não fornecidos"}), 400

    if not all([data.get('start_time'), data.get('max_capacity')]):
        return jsonify({"error": "Campos obrigatórios faltando! Campos: start_time, max_capacity"}), 400

    try:
        tour = tour_service.find_tour(tour_id)
        if not tour:
            return jsonify({"error": "Tour não encontrado"}), 404
        if not is_tour_owner(tour, current_user):
            return jsonify({"error": "Acesso negado"}), 403
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

@tour_bp.route('/<int:tour_id>/instance/<int:instance_id>', methods=['PATCH'])
@token_required
@role_required(UserRole.GUIDE)
def update_tour_instance(current_user, tour_id, instance_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Dados da instância de tour não fornecidos"}), 400

    tour = tour_service.find_tour(tour_id)
    if not tour:
        return jsonify({"error": "Tour não encontrado"}), 404
    if not is_tour_owner(tour, current_user):
        return jsonify({"error": "Acesso negado"}), 403

    instance = tour_service.find_tour_instance(tour_id, instance_id)
    if not instance:
        return jsonify({"error": "Instância de tour não encontrada para este tour"}), 404

    try:
        update = TourInstanceUpdateModel(**data).model_dump(mode='json', exclude_none=True)
    except ValidationError as e:
        return jsonify({"error": f"Dados da instância inválidos: {e}"}), 400

    accepted = tour_service.count_accepted_requests(instance_id)
    max_capacity = update.get('max_capacity', instance['max_capacity'])
    if max_capacity < accepted:
        return jsonify({"error": f"Já existem {accepted} participantes aceitos. As vagas não podem ser menores que isso."}), 409
    if update.get('registration') == RegistrationStatus.OPEN.value and accepted >= max_capacity:
        return jsonify({"error": "Não há vagas livres. Aumente as vagas antes de reabrir as solicitações."}), 409

    try:
        supabase.table("tour_instance").update(update).eq("id", instance_id).execute()
        return jsonify({"message": "Instância de tour atualizada com sucesso"}), 200
    except Exception as e:
        current_app.logger.error(f"Erro ao atualizar instância de tour: {e}")
        return jsonify({"error": "Erro ao atualizar instância de tour"}), 500

@tour_bp.route('/<int:tour_id>/instance/<int:instance_id>', methods=['GET'])
@token_required
def get_tour_instance(current_user, tour_id, instance_id):
    """
    Obter detalhes de uma instância de tour
    ---
    tags:
        - Tours
    parameters:
        - in: path
          name: tour_id
          description: ID do tour
          required: true
          type: integer
        - in: path
          name: instance_id
          description: ID da instância de tour
          required: true
          type: integer
    responses:
        200:
            description: Detalhes da instância de tour obtidos com sucesso
            schema:
                type: object
                properties:
                    start_time:
                        type: string
                        format: date-time
                    max_capacity:
                        type: integer
                    current_capacity:
                        type: integer
                    chat_id:
                        type: integer
        403:
            description: Acesso negado
            schema:
                type: object
                properties:
                    error:
                        type: string
        404:
            description: Tour ou instância de tour não encontrado
            schema:
                type: object
                properties:
                    error:
                        type: string
        500:
            description: Erro ao obter detalhes da instância de tour
            schema:
                type: object
                properties:
                    error:
                        type: string
    """
    try:
        tour = tour_service.find_tour(tour_id)
        if not tour:
            return jsonify({"error": "Tour não encontrado"}), 404
        instance = tour_service.find_tour_instance(tour_id, instance_id)
        if not instance:
            return jsonify({"error": "Instância de tour não encontrada para este tour"}), 404
    except Exception as e:
        return jsonify({"error": f"Erro ao verificar instância de tour: {e}"}), 500

    chat_id = None
    if _is_on_tour(tour, instance_id, current_user):
        chat_response = supabase.table("chat").select("*").eq("tour_instance_id", instance_id).execute()
        chat_id = chat_response.data[0]['id'] if chat_response.data else None

    return jsonify({
        "start_time": instance['start_time'],
        "max_capacity": instance['max_capacity'],
        "current_capacity": tour_service.count_accepted_requests(instance_id),
        "chat_id": chat_id
    }), 200
