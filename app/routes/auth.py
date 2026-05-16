from flask import Blueprint, current_app, request, jsonify
from pydantic import ValidationError
from app.models.user_models import UserCreateModel # Seu DTO
from app.services.cnpj_service import buscar_dados_cnpj
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from app.services.supabase_service import supabase

cnaes_turismo = [7911200, 7912100]
cnaes_eventos = [8230001]

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def add_user():
    """
    Cadastrar um novo usuário
    ---
    tags:
        - Users
    requestBody:
        required: true
        content:
            application/json:
                schema:
                    type: object
                    properties:
                        email:
                            type: string
                        password:
                            type: string
                        role:
                            type: string
                        cnpj:
                            type: string
    responses:
        201:
            description: Usuário criado com sucesso
        400:
            description: Dados de usuário ausentes ou inválidos
        500:
            description: Erro ao salvar usuário no banco de dados
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Body ausente"}), 400
    
    # fazer hash da password
    password = data.get('password')
    if not password:
        return jsonify({"error": "Password obrigatório"}), 400
    
    data = data.copy()
    data['password'] = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    
    try:
        user = UserCreateModel(**data)
    except ValidationError as e:
        return jsonify({"error": f"Dados de usuário inválidos: {e}"}), 400
    except Exception as e:
        return jsonify({"error": f"Erro ao criar usuário: {e}"}), 400

    if user.role and user.role != "TOURIST":
        if not user.cnpj: # não é turista: cnpj é requerido
            return jsonify({"error": "Campos requeridos faltando: CNPJ"}), 400

        # limpeza no cnpj (tirando pontuações)
        user.cnpj = ''.join(filter(str.isdigit, user.cnpj))
        resultado = buscar_dados_cnpj(user.cnpj)

        if resultado is None:
            return jsonify({"error": "CNPJ inválido ou inacessível"}), 400
        if user.role == "GUIDE" and resultado.get('cnae_fiscal') not in cnaes_turismo:
            return jsonify({"error": "CNPJ não é de um guia turístico"}), 400
        if user.role == "EVENT_PROMOTER" and resultado.get('cnae_fiscal') not in cnaes_eventos:
            return jsonify({"error": "CNPJ não é de um promotor de eventos"}), 400
        
    try:
        response = supabase.table("user").insert(user.dict()).execute()
        user_data = response.data
        if not user_data:
            return jsonify({"error": "Erro ao salvar usuário no banco de dados"}), 500
        return jsonify({"message": "Usuário criado com sucesso", "user_id": user_data[0]['user_id']}), 201
    except Exception as e:
        current_app.logger.exception(e)
        return jsonify({"error": "Erro ao salvar usuário"}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Autenticar um usuário e gerar um token JWT
    ---
    tags:
        - Users
    requestBody:
        required: true
        content:
            application/json:
                schema:
                    type: object
                    properties:
                        email:
                            type: string
                        password:
                            type: string
    responses:
        200:
            description: Login bem-sucedido, retorna token JWT
        400:
            description: Dados de login ausentes ou inválidos
        401:
            description: Credenciais inválidas
        500:
            description: Erro ao buscar usuário no banco de dados
    """
    
    data = request.get_json()
    if not data:
        return jsonify(message="Dados de login não fornecidos!"), 400
    if "email" not in data or "password" not in data:
        return jsonify(message="Campos 'email' e 'password' são obrigatórios!"), 400

    try:
        supabase_response = supabase.table("user").select("user_id, email, password, role").eq("email", data["email"]).execute()
        if not supabase_response.data:
            return jsonify(message="Credenciais inválidas!"), 401
        user = supabase_response.data[0]
    except Exception as e:
        return jsonify(message=f"Erro ao buscar usuário no banco de dados: {e}"), 500

    if not bcrypt.checkpw(data["password"].encode('utf-8'), user["password"].encode('utf-8')):
        return jsonify(message="Credenciais inválidas!"), 401

    # Gerar o token com expiração
    token = jwt.encode(
        {"user_id": user['user_id'], "role": user['role'], "exp": datetime.now(timezone.utc) + timedelta(minutes=30)},
        current_app.config['AUTH_CRYPT_KEY'],
        algorithm="HS256"
    )
    return jsonify(token=token)
