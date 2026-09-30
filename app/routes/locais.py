from flask import Blueprint, current_app, jsonify, request
from app.utils.auth import token_required
from app.services import local_service

locais_bp = Blueprint('locais', __name__)

def _ponto(prefixo=''):
    try:
        return float(request.args[f'{prefixo}lat']), float(request.args[f'{prefixo}lon'])
    except (KeyError, ValueError):
        return None

@locais_bp.route('/busca', methods=['GET'])
@token_required
def buscar_locais(current_user):
    texto = (request.args.get('q') or '').strip()
    if not texto:
        return jsonify([]), 200
    try:
        return jsonify(local_service.buscar(texto, _ponto())), 200
    except Exception as e:
        current_app.logger.error(f"Erro na busca de locais: {e}")
        return jsonify({"error": "A busca de locais não respondeu. Tente de novo em instantes."}), 502

@locais_bp.route('/ponto', methods=['GET'])
@token_required
def endereco_do_ponto(current_user):
    ponto = _ponto()
    if not ponto:
        return jsonify({"error": "Informe lat e lon válidos"}), 400
    try:
        return jsonify(local_service.endereco_do_ponto(*ponto)), 200
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar o endereço do ponto: {e}")
        return jsonify({"error": "Não conseguimos achar o endereço desse ponto."}), 502
