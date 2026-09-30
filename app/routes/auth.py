from flask import Blueprint, current_app, request, jsonify
from pydantic import ValidationError
from app.models.user_models import UserCreateModel # Seu DTO
from app.services.cnpj_service import buscar_dados_cnpj
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from app.services.supabase_service import supabase
from app.services import foto_service, senha_service
from app.services.email_service import EmailIndisponivel
from app.models.enums import UserRole

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
                        username:
                            type: string
                        first_name:
                            type: string
                        last_name:
                            type: string
                        email:
                            type: string
                        password:
                            type: string
                        phone:
                            type: string
                        role:
                            type: enum
                            enum: [TOURIST, GUIDE, EVENT_PROMOTER]
                        photo:
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
    foto = request.files.get('photo')
    data = request.form.to_dict() if request.content_type and request.content_type.startswith('multipart/') else request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Body ausente"}), 400
    data.setdefault('photo', '')
    
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

    if user.role == UserRole.ADMIN:
        return jsonify({"error": "Não é possível se cadastrar como administrador"}), 403

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
        user_id = user_data[0]['user_id']
        if foto:
            try:
                url = foto_service.enviar_foto_de_perfil(foto, user_id)
                supabase.table("user").update({"photo": url}).eq("user_id", user_id).execute()
            except Exception as e:
                current_app.logger.warning(f"Conta criada sem foto: {e}")
        return jsonify({"message": "Usuário criado com sucesso", "user_id": user_id}), 201
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
            return jsonify(message="Email ou senha não conferem. Confere e tenta de novo."), 401
        user = supabase_response.data[0]
    except Exception as e:
        return jsonify(message=f"Erro ao buscar usuário no banco de dados: {e}"), 500

    if not bcrypt.checkpw(data["password"].encode('utf-8'), user["password"].encode('utf-8')):
        return jsonify(message="Email ou senha não conferem. Confere e tenta de novo."), 401

    # Gerar o token com expiração
    token = jwt.encode(
        {"user_id": user['user_id'], "role": user['role'], "exp": datetime.now(timezone.utc) + timedelta(days=30)},
        current_app.config['AUTH_CRYPT_KEY'],
        algorithm="HS256"
    )
    return jsonify(token=token, user_id=user['user_id'], role=user['role']), 200

@auth_bp.route('/esqueci-senha', methods=['POST'])
def esqueci_senha():
    email = ((request.get_json(silent=True) or {}).get("email") or "").strip().lower()
    if not email:
        return jsonify(error="Coloque o email da sua conta."), 400
    try:
        senha_service.pedir_troca(email)
    except EmailIndisponivel:
        return jsonify(error="O envio de email ainda não está funcionando. Fale com a equipe do Viajá."), 503
    except Exception as e:
        current_app.logger.error(f"Erro ao pedir troca de senha: {e}")
        return jsonify(error="Não conseguimos mandar o email agora. Tente de novo em alguns minutos."), 500
    return jsonify(message="Se esse email tiver uma conta, mandamos um link para trocar a senha."), 200

@auth_bp.route('/redefinir-senha', methods=['POST'])
def redefinir_senha():
    data = request.get_json(silent=True) or {}
    codigo = data.get("codigo") or ""
    senha = data.get("password") or ""
    if len(senha) < 8:
        return jsonify(error="A senha precisa ter pelo menos 8 caracteres."), 400
    try:
        trocou = senha_service.trocar_senha(codigo, senha)
    except Exception as e:
        current_app.logger.error(f"Erro ao trocar senha: {e}")
        return jsonify(error="Não conseguimos trocar a senha agora. Tente de novo."), 500
    if not trocou:
        return jsonify(error="Esse link não vale mais. Peça um novo na tela de entrar."), 400
    return jsonify(message="Senha trocada. Já pode entrar com a senha nova."), 200
