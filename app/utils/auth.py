from functools import wraps
from flask import current_app, jsonify, request
import jwt
from app.models.enums import UserRole

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # verifica se o header existe
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"message": "Token é necessário ou malformado!"}), 401

        try:
            # extrai e decodifica o token
            token = auth_header.split(" ")[1]
            data = jwt.decode(
                token,
                current_app.config['AUTH_CRYPT_KEY'],
                algorithms=["HS256"]
            )
            # adiciona os dados do usuário no contexto da requisição
            current_user = {"user_id": data["user_id"], "role": data.get("role")}
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token expirado!"}), 401
        except Exception:
            return jsonify({"message": "Token inválido!"}), 401

        # passa o usuário logado para a função da rota
        return f(current_user, *args, **kwargs)

    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(current_user, *args, **kwargs):
            if current_user.get('role') not in roles:
                return jsonify({"error": "Acesso negado"}), 403
            return f(current_user, *args, **kwargs)
        return decorated
    return decorator

def is_tour_owner(tour, current_user):
    return tour['created_by_id'] == current_user['user_id']

def is_admin(current_user):
    return current_user.get('role') == UserRole.ADMIN

def can_moderate_tour(tour, current_user):
    return is_tour_owner(tour, current_user) or is_admin(current_user)
