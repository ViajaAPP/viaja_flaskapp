from datetime import datetime, timezone
from flask import Blueprint, current_app, jsonify, request
from pydantic import ValidationError
from app.utils.auth import token_required, role_required
from app.models.enums import UserRole
from app.models.address_models import AddressCreateModel
from app.services import evento_service, foto_service, tour_service

eventos_bp = Blueprint('eventos', __name__)

CAMPOS_EDITAVEIS = ("title", "description", "start_time", "end_time", "place_name", "price", "capacity", "photo", "photo_credit")
CAMPOS_DO_ENDERECO = ("uf", "city", "neighborhood", "street")

def _numero(nome):
    try:
        return float(request.args[nome])
    except (KeyError, ValueError):
        return None

def _data_valida(texto):
    try:
        return datetime.fromisoformat(str(texto).replace('Z', '+00:00'))
    except (TypeError, ValueError):
        return None

def _campos(data, exigir):
    campos = {c: data[c] for c in CAMPOS_EDITAVEIS if c in data}
    if exigir:
        faltando = [c for c in ("title", "description", "start_time") + CAMPOS_DO_ENDERECO if not data.get(c)]
        if faltando or data.get("lat") in (None, "") or data.get("lon") in (None, ""):
            return None, "Preencha nome, descrição, dia e horário, e marque o local no mapa."
    for campo in ("start_time", "end_time"):
        if campo in campos and campos[campo]:
            quando = _data_valida(campos[campo])
            if not quando:
                return None, "Dia ou horário inválido."
            if campo == "start_time" and quando <= datetime.now(timezone.utc):
                return None, "Escolha um dia e horário que ainda não passaram."
            campos[campo] = quando.isoformat()
        elif campo in campos:
            campos[campo] = None
    if "price" in campos:
        campos["price"] = max(float(campos["price"] or 0), 0)
    if "capacity" in campos:
        campos["capacity"] = int(campos["capacity"]) if campos["capacity"] else None
    if any(c in data for c in CAMPOS_DO_ENDERECO):
        cep = ''.join(ch for ch in str(data.get('cep') or '') if ch.isdigit())
        try:
            endereco = AddressCreateModel(
                cep=cep if len(cep) == 8 else None, uf=data.get("uf"), city=data.get("city"),
                neighborhood=data.get("neighborhood") or "", street=data.get("street") or "",
                number=str(data.get("number") or "").strip() or "S/N",
                lat=data.get("lat"), lon=data.get("lon"),
            )
        except ValidationError:
            return None, "Endereço inválido."
        campos["address_id"] = tour_service.find_or_create_address(endereco)
    return campos, None

def _evento_ou_erro(evento_id, current_user, precisa_ser_dono=False):
    evento = evento_service.buscar(evento_id)
    if not evento:
        return None, (jsonify({"error": "Evento não encontrado"}), 404)
    dono = evento["organizer_id"] == current_user["user_id"]
    admin = current_user.get("role") == UserRole.ADMIN
    if precisa_ser_dono and not dono:
        return None, (jsonify({"error": "Só quem organiza pode mexer nesse evento"}), 403)
    if evento["status"] != "PUBLISHED" and not (dono or admin):
        return None, (jsonify({"error": "Evento não encontrado"}), 404)
    return evento, None

@eventos_bp.route('/', methods=['GET'])
@token_required
def listar(current_user):
    lat, lon = _numero('lat'), _numero('lon')
    try:
        return jsonify(evento_service.listar_publicados(
            current_user['user_id'],
            centro=(lat, lon) if lat is not None and lon is not None else None,
            raio_km=_numero('raio'),
            gratuito=request.args.get('gratuito') == '1',
            limite=int(_numero('limite')) if _numero('limite') else None,
            ordem=request.args.get('ordem') or 'data',
        )), 200
    except Exception as e:
        current_app.logger.error(f"Erro ao listar eventos: {e}")
        return jsonify({"error": "Não conseguimos carregar os eventos agora."}), 500

@eventos_bp.route('/meus', methods=['GET'])
@token_required
@role_required(UserRole.EVENT_PROMOTER, UserRole.GUIDE, UserRole.ADMIN)
def meus(current_user):
    return jsonify(evento_service.listar_do_organizador(current_user['user_id'])), 200

@eventos_bp.route('/vou', methods=['GET'])
@token_required
def vou(current_user):
    return jsonify(evento_service.listar_onde_vou(current_user['user_id'])), 200

@eventos_bp.route('/analise', methods=['GET'])
@token_required
@role_required(UserRole.ADMIN)
def analise(current_user):
    return jsonify(evento_service.listar_para_analise()), 200

@eventos_bp.route('/foto', methods=['POST'])
@token_required
@role_required(UserRole.EVENT_PROMOTER, UserRole.GUIDE, UserRole.ADMIN)
def enviar_foto(current_user):
    arquivo = request.files.get('photo')
    if not arquivo:
        return jsonify({"error": "Escolha uma foto"}), 400
    try:
        return jsonify({"photo": foto_service.enviar_capa_de_passeio(arquivo, f"eventos-{current_user['user_id']}")}), 200
    except foto_service.FotoInvalida as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Erro ao enviar foto do evento: {e}")
        return jsonify({"error": "Não conseguimos enviar a foto. Tente de novo."}), 500

@eventos_bp.route('/<int:evento_id>', methods=['GET'])
@token_required
def detalhe(current_user, evento_id):
    evento, erro = _evento_ou_erro(evento_id, current_user)
    if erro:
        return erro
    return jsonify(evento_service.detalhe(evento, current_user['user_id'])), 200

@eventos_bp.route('/', methods=['POST'])
@token_required
@role_required(UserRole.EVENT_PROMOTER, UserRole.GUIDE, UserRole.ADMIN)
def criar(current_user):
    campos, erro = _campos(request.get_json(silent=True) or {}, exigir=True)
    if erro:
        return jsonify({"error": erro}), 400
    try:
        evento = evento_service.criar(current_user['user_id'], campos)
        return jsonify({"message": "Evento enviado para análise.", "id": evento["id"]}), 201
    except Exception as e:
        current_app.logger.error(f"Erro ao criar evento: {e}")
        return jsonify({"error": "Não conseguimos salvar o evento. Tente de novo."}), 500

@eventos_bp.route('/<int:evento_id>', methods=['PATCH'])
@token_required
@role_required(UserRole.EVENT_PROMOTER, UserRole.GUIDE, UserRole.ADMIN)
def editar(current_user, evento_id):
    evento, erro = _evento_ou_erro(evento_id, current_user, precisa_ser_dono=True)
    if erro:
        return erro
    if evento["status"] in ("CANCELLED", "DONE"):
        return jsonify({"error": "Esse evento já foi encerrado."}), 409
    campos, erro = _campos(request.get_json(silent=True) or {}, exigir=False)
    if erro:
        return jsonify({"error": erro}), 400
    atualizado = evento_service.atualizar(evento, campos)
    return jsonify({"message": "Evento salvo.", "status": atualizado["status"]}), 200

@eventos_bp.route('/<int:evento_id>/cancelar', methods=['POST'])
@token_required
@role_required(UserRole.EVENT_PROMOTER, UserRole.GUIDE, UserRole.ADMIN)
def cancelar(current_user, evento_id):
    evento, erro = _evento_ou_erro(evento_id, current_user, precisa_ser_dono=True)
    if erro:
        return erro
    evento_service.cancelar(evento)
    return jsonify({"message": "Evento cancelado."}), 200

@eventos_bp.route('/<int:evento_id>/analise', methods=['POST'])
@token_required
@role_required(UserRole.ADMIN)
def analisar(current_user, evento_id):
    evento = evento_service.buscar(evento_id)
    if not evento:
        return jsonify({"error": "Evento não encontrado"}), 404
    data = request.get_json(silent=True) or {}
    aprovar = bool(data.get("aprovar"))
    motivo = (data.get("motivo") or "").strip()
    if not aprovar and not motivo:
        return jsonify({"error": "Conte o motivo para o organizador saber o que ajustar."}), 400
    evento_service.analisar(evento, current_user['user_id'], aprovar, motivo)
    return jsonify({"message": "Evento aprovado." if aprovar else "Evento devolvido com o motivo."}), 200

@eventos_bp.route('/<int:evento_id>/vou', methods=['POST', 'DELETE'])
@token_required
def presenca(current_user, evento_id):
    evento, erro = _evento_ou_erro(evento_id, current_user)
    if erro:
        return erro
    if evento["status"] != "PUBLISHED":
        return jsonify({"error": "Esse evento não está aberto."}), 409
    if not evento_service.marcar_presenca(evento, current_user['user_id'], request.method == 'POST'):
        return jsonify({"error": "Esse evento já está lotado."}), 409
    return jsonify({"message": "Presença salva."}), 200
