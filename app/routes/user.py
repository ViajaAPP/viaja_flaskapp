from flask import Blueprint, current_app, request, jsonify
from app.services.supabase_service import supabase
from app.services import foto_service, cripto_service, perfil_service
from app.utils.auth import token_required

user_bp = Blueprint('user', __name__)

CAMPOS_EDITAVEIS = ("first_name", "last_name", "phone")
CAMPOS_OBRIGATORIOS = {"first_name": "Conta pra gente seu nome", "last_name": "Conta pra gente seu sobrenome"}

def _foto_atual(user_id):
    response = supabase.table("user").select("photo").eq("user_id", user_id).execute()
    return response.data[0]['photo'] if response.data else None

@user_bp.route('/<int:user_id>/publico', methods=['GET'])
@token_required
def perfil_publico(current_user, user_id):
    try:
        perfil = perfil_service.perfil_publico(user_id, current_user['user_id'])
    except Exception as e:
        current_app.logger.error(f"Erro ao abrir perfil público: {e}")
        return jsonify({"error": "Não conseguimos abrir esse perfil agora. Tente de novo."}), 500
    if not perfil:
        return jsonify({"error": "Perfil não encontrado"}), 404
    return jsonify(perfil), 200

@user_bp.route('/me', methods=['PATCH'])
@token_required
def update_me(current_user):
    data = request.get_json() or {}
    changes = {campo: str(data[campo]).strip() for campo in CAMPOS_EDITAVEIS if campo in data and data[campo] is not None}
    erros = {campo: mensagem for campo, mensagem in CAMPOS_OBRIGATORIOS.items() if campo in changes and not changes[campo]}
    if erros:
        return jsonify({"error": "Confira os campos destacados", "fields": erros}), 400
    if not changes:
        return jsonify({"error": "Nada para atualizar"}), 400
    if "phone" in changes:
        changes["phone"] = cripto_service.cifrar(changes["phone"], "user.phone")
    try:
        supabase.table("user").update(changes).eq("user_id", current_user['user_id']).execute()
        return jsonify({"message": "Perfil salvo"}), 200
    except Exception as e:
        current_app.logger.error(f"Erro ao atualizar perfil: {e}")
        return jsonify({"error": "Erro ao atualizar perfil"}), 500

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
