from flask import Blueprint, current_app, jsonify, request
from app.utils.auth import token_required
from app.services import aviso_service

avisos_bp = Blueprint('avisos', __name__)

@avisos_bp.route('/', methods=['GET'])
@token_required
def listar_avisos(current_user):
    try:
        return jsonify({
            "itens": aviso_service.listar(current_user['user_id']),
            "nao_lidas": aviso_service.contar_nao_lidas(current_user['user_id']),
        }), 200
    except Exception as e:
        current_app.logger.error(f"Erro ao listar avisos: {e}")
        return jsonify({"error": "Não conseguimos carregar seus avisos."}), 500

@avisos_bp.route('/contagem', methods=['GET'])
@token_required
def contar_avisos(current_user):
    try:
        return jsonify({"nao_lidas": aviso_service.contar_nao_lidas(current_user['user_id'])}), 200
    except Exception as e:
        current_app.logger.error(f"Erro ao contar avisos: {e}")
        return jsonify({"nao_lidas": 0}), 200

@avisos_bp.route('/lidas', methods=['POST'])
@token_required
def marcar_lidas(current_user):
    ids = (request.get_json(silent=True) or {}).get('ids')
    try:
        aviso_service.marcar_lidas(current_user['user_id'], [int(i) for i in ids] if ids else None)
        return jsonify({"message": "Avisos lidos"}), 200
    except Exception as e:
        current_app.logger.error(f"Erro ao marcar avisos: {e}")
        return jsonify({"error": "Não conseguimos marcar os avisos como lidos."}), 500
