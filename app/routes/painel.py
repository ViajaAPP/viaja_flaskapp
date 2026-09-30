from flask import Blueprint, current_app, jsonify
from app.utils.auth import token_required, role_required
from app.models.enums import UserRole
from app.services import painel_service

painel_bp = Blueprint('painel', __name__)

@painel_bp.route('/pedidos', methods=['GET'])
@token_required
@role_required(UserRole.GUIDE)
def pedidos(current_user):
    try:
        return jsonify(painel_service.pedidos_do_guia(current_user['user_id'])), 200
    except Exception as e:
        current_app.logger.error(f"Erro nos pedidos do painel: {e}")
        return jsonify({"error": "Não conseguimos carregar seus pedidos."}), 500

@painel_bp.route('/agenda', methods=['GET'])
@token_required
@role_required(UserRole.GUIDE)
def agenda(current_user):
    try:
        return jsonify(painel_service.agenda_do_guia(current_user['user_id'])), 200
    except Exception as e:
        current_app.logger.error(f"Erro na agenda do painel: {e}")
        return jsonify({"error": "Não conseguimos carregar sua agenda."}), 500

@painel_bp.route('/contagem', methods=['GET'])
@token_required
@role_required(UserRole.GUIDE)
def contagem(current_user):
    try:
        return jsonify({"pendentes": painel_service.contagem_do_guia(current_user['user_id'])}), 200
    except Exception as e:
        current_app.logger.error(f"Erro na contagem do painel: {e}")
        return jsonify({"pendentes": 0}), 200

@painel_bp.route('/viagens', methods=['GET'])
@token_required
def viagens(current_user):
    try:
        return jsonify(painel_service.viagens_do_viajante(current_user['user_id'])), 200
    except Exception as e:
        current_app.logger.error(f"Erro nas viagens: {e}")
        return jsonify({"error": "Não conseguimos carregar suas viagens."}), 500
