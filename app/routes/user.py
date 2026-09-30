from flask import Blueprint, current_app, request, jsonify
from app.services.supabase_service import supabase
from app.services import foto_service
from app.utils.auth import token_required

user_bp = Blueprint('user', __name__)

def _foto_atual(user_id):
    response = supabase.table("user").select("photo").eq("user_id", user_id).execute()
    return response.data[0]['photo'] if response.data else None

@user_bp.route('/me/photo', methods=['POST'])
@token_required
def upload_my_photo(current_user):
    arquivo = request.files.get('photo')
    if not arquivo:
        return jsonify({"error": "Escolha uma foto"}), 400
    try:
        antiga = _foto_atual(current_user['user_id'])
        url = foto_service.enviar_foto_de_perfil(arquivo, current_user['user_id'])
        supabase.table("user").update({"photo": url}).eq("user_id", current_user['user_id']).execute()
        foto_service.apagar_foto(antiga)
        return jsonify({"photo": url}), 200
    except foto_service.FotoInvalida as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Erro ao enviar foto de perfil: {e}")
        return jsonify({"error": "Erro ao enviar foto de perfil"}), 500

@user_bp.route('/me/photo', methods=['DELETE'])
@token_required
def delete_my_photo(current_user):
    try:
        antiga = _foto_atual(current_user['user_id'])
        supabase.table("user").update({"photo": ""}).eq("user_id", current_user['user_id']).execute()
        foto_service.apagar_foto(antiga)
        return jsonify({"photo": ""}), 200
    except Exception as e:
        current_app.logger.error(f"Erro ao remover foto de perfil: {e}")
        return jsonify({"error": "Erro ao remover foto de perfil"}), 500
