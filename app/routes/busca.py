from flask import Blueprint, current_app, jsonify, request
from app.utils.auth import token_required
from app.services import busca_service

busca_bp = Blueprint('busca', __name__)

def _numero(nome):
    try:
        return float(request.args[nome])
    except (KeyError, ValueError):
        return None

def _centro():
    lat, lon = _numero('lat'), _numero('lon')
    return (lat, lon) if lat is not None and lon is not None else None

@busca_bp.route('/sugestoes', methods=['GET'])
@token_required
def sugestoes(current_user):
    texto = (request.args.get('q') or '').strip()
    if not texto:
        return jsonify({"cidades": [], "passeios": [], "lugares": []}), 200
    try:
        return jsonify(busca_service.sugestoes(texto, _centro())), 200
    except Exception as e:
        current_app.logger.error(f"Erro nas sugestões de busca: {e}")
        return jsonify({"error": "A busca não respondeu agora. Tente de novo."}), 500

@busca_bp.route('/destinos', methods=['GET'])
@token_required
def destinos(current_user):
    try:
        return jsonify(busca_service.destinos_em_alta()), 200
    except Exception as e:
        current_app.logger.error(f"Erro nos destinos em alta: {e}")
        return jsonify([]), 200

@busca_bp.route('/passeios', methods=['GET'])
@token_required
def passeios(current_user):
    try:
        resultados = busca_service.buscar_passeios(
            current_user['user_id'],
            centro=_centro(),
            raio_km=_numero('raio'),
            texto=(request.args.get('q') or '').strip(),
            preco_max=_numero('preco_max'),
            gratuito=request.args.get('gratuito') == '1',
            quando=request.args.get('quando') or None,
            nota_min=_numero('nota_min'),
            ordem=request.args.get('ordem') or 'relevancia',
        )
        limite = _numero('limite')
        return jsonify(resultados[:int(limite)] if limite else resultados), 200
    except Exception as e:
        current_app.logger.error(f"Erro na busca de passeios: {e}")
        return jsonify({"error": "Não conseguimos buscar os passeios agora. Tente de novo."}), 500
