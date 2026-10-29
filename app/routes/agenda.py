from flask import Blueprint, current_app, request, jsonify
from app.services import agenda_service
from app.utils.auth import token_required

agenda_bp = Blueprint('agenda', __name__)

@agenda_bp.route('/conflitos', methods=['GET'])
@token_required
def conflitos(current_user):
    instancia, evento = request.args.get('instancia'), request.args.get('evento')
    try:
        if instancia and instancia.isdigit():
            janela, alvo = agenda_service.janela_da_instancia(int(instancia)), ("passeio", int(instancia))
        elif evento and evento.isdigit():
            janela, alvo = agenda_service.janela_do_evento(int(evento)), ("evento", int(evento))
        else:
            return jsonify({"error": "Informe a data do passeio ou o evento."}), 400
        if not janela:
            return jsonify({"error": "Não achamos esse horário."}), 404
        return jsonify({"conflitos": agenda_service.conflitos(current_user['user_id'], *janela, ignorar=alvo)}), 200
    except Exception as e:
        current_app.logger.error(f"Erro ao conferir conflitos de agenda: {e}")
        return jsonify({"error": "Não conseguimos conferir sua agenda agora."}), 500
