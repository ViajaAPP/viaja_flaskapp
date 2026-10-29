from datetime import date
from flask import Blueprint, current_app, request, jsonify
from app.services import roteiro_service, busca_service
from app.utils.auth import token_required

roteiro_bp = Blueprint('roteiro', __name__)

MAXIMO_DE_DIAS = 4

@roteiro_bp.route('/cidades', methods=['GET'])
@token_required
def cidades(current_user):
    try:
        return jsonify(busca_service.destinos_em_alta(limite=12)), 200
    except Exception as e:
        current_app.logger.error(f"Erro ao listar cidades do roteiro: {e}")
        return jsonify({"error": "Não conseguimos carregar as cidades agora."}), 500

@roteiro_bp.route('/', methods=['GET'])
@token_required
def montar(current_user):
    cidade = (request.args.get('cidade') or '').strip()
    uf = (request.args.get('uf') or '').strip().upper()
    if not cidade or len(uf) != 2:
        return jsonify({"error": "Escolha a cidade do roteiro."}), 400
    try:
        primeiro_dia = date.fromisoformat(request.args.get('inicio') or '')
    except ValueError:
        return jsonify({"error": "Escolha o primeiro dia da viagem."}), 400
    try:
        dias = max(1, min(MAXIMO_DE_DIAS, int(request.args.get('dias') or 1)))
    except ValueError:
        dias = 1
    try:
        roteiro = roteiro_service.montar(cidade, uf, primeiro_dia, dias)
    except Exception as e:
        current_app.logger.error(f"Erro ao montar roteiro: {e}")
        return jsonify({"error": "Não conseguimos montar o roteiro agora. Tente de novo."}), 500
    if roteiro is None:
        return jsonify({"error": "Não achamos essa cidade."}), 404
    return jsonify(roteiro), 200
