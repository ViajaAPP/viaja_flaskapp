import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import time
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, EmailStr
from typing import Optional
from supabase import create_client, Client
import queue
import threading
import requests
import bcrypt
import jwt
import platform
from pyngrok import ngrok

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
AUTH_CRYPT_KEY = os.getenv('AUTH_CRYPT_KEY')

supabase: Client = create_client(url, key)
app = Flask(__name__)

cnaes_turismo = [7911200, 7912100]
cnaes_eventos = [8230001]

class UserType(BaseModel):
    id: int
    name: str

class UserModel(BaseModel):
    id: Optional[int] = None
    username: str
    email: EmailStr
    password: str
    phone: str
    type_id: int
    cnpj: Optional[str] = None

    def dict(self, *args, **kwargs):
        data = super().dict(*args, **kwargs)
        return data

    def dict_not_null(self, *args, **kwargs):
        data = self.dict(*args, **kwargs)
        return {k: v for k, v in data.items() if v is not None}

class ChatModel(BaseModel):
    id: int
    name: str
    created_at: str

class MessageModel(BaseModel):
    id: int
    sent_at: datetime
    content: str
    chat_id: int
    user_id: int

msg_queue = queue.Queue()

def message_processor():
    """Worker que processa a fila de mensagens e salva no Supabase"""
    while True:
        dados = msg_queue.get()

        if dados is None:
            break

        try:
            with app.app_context():
                new_msg = MessageModel(
                    content=dados.get('content'),
                    chat_id=dados.get('chat_id'),
                    user_id=dados.get('user_id')
                )

                supabase.table("messages").insert(new_msg.dict()).execute()
                print("Mensagem enviada com sucesso!")

        except Exception as e:
            print(f"Erro ao processar mensagem na fila: {e}")

        finally:
            msg_queue.task_done()

# inicia o serviço em background
threading.Thread(target=message_processor, daemon=True).start()

@app.route('/')
def hello():
    try:
        # verificar conexão com o supabase
        response = supabase.rpc("health_check").execute()
        # verifica status da fila
        qt_mensagens_fila = msg_queue.qsize()
        db_status = "offline"
        if response.data == 1:
            db_status = "online"
        return jsonify({"database": db_status, "msg_queue_size": qt_mensagens_fila})
    except Exception as e:
        return f"Erro ao conectar com o Supabase: {e}"

@app.route('/message', methods=['POST'])
def send_message():
    dados = request.json
    if not dados.get('content') or not dados.get('chat_id') or not dados.get('user_id'):
        return jsonify({"error": "Campos requeridos faltando"}), 400

    # a view apenas repassa para o controller (via queue)
    msg_queue.put(dados)
    return jsonify({"status": "Mensagem enviada à fila"}), 202

@app.route('/register', methods=['POST'])
def add_user():
    try:
        # fazer hash da password
        password = request.json.get('password')
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        request.json['password'] = hashed_password.decode('utf-8')
        user = UserModel(**request.json)
        if not user.dict():
            return jsonify({"error": "Campos requeridos faltando"}), 400

        if user.type_id != 1:
            # não é turista: cnpj é requerido
            if not user.cnpj:
                return jsonify({"error": "Campos requeridos faltando: CNPJ"}), 400

            # limpeza no cnpj (tirando pontuações)
            user.cnpj = ''.join(filter(str.isdigit, user.cnpj))

            # api do brasil api para buscar cep
            tentativas = 0
            resultado_api = None
            while resultado_api is None and tentativas < 4:
                tentativas += 1
                resultado_api = requests.get(f"https://brasilapi.com.br/api/cnpj/v1/{user.cnpj}")
                # se deu erro 400, retorna erro geral
                if resultado_api.status_code == 400:
                    return jsonify({"error": "CNPJ Inválido"}), 400

                if resultado_api.status_code != 200:
                    resultado_api = None
                    time.sleep(1)  # espera um pouco antes de tentar novamente
                    continue

                resultado_api = resultado_api.json()
                if user.type_id == 2 and resultado_api.get('cnae_fiscal') not in cnaes_turismo:
                    return jsonify({"error": "CNPJ não é de um guia turístico"}), 400
                if user.type_id == 3 and resultado_api.get('cnae_fiscal') not in cnaes_eventos:
                    return jsonify({"error": "CNPJ não é de um promotor de eventos"}), 400

        # salvar no banco
        return supabase.table("user").insert(user.dict_not_null()).execute().data, 201
    except Exception as e:
        return {"erro": str(e)}, 400

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data:
        return jsonify(message="Dados de login não fornecidos!"), 400
    if "email" not in data or "password" not in data:
        return jsonify(message="Campos 'email' e 'password' são obrigatórios!"), 400

    try:
        supabase_response = supabase.table("user").select("user_id, email, password").eq("email", data["email"]).execute()
        if not supabase_response.data:
            return jsonify(message="Credenciais inválidas!"), 401
        user = supabase_response.data[0]
    except Exception as e:
        return jsonify(message=f"Erro ao buscar usuário no banco de dados: {e}"), 500

    if not bcrypt.checkpw(data["password"].encode('utf-8'), user["password"].encode('utf-8')):
        return jsonify(message="Credenciais inválidas!"), 401

    # Gerar o token com expiração
    token = jwt.encode(
        {"user_id": user['user_id'], "exp": datetime.now(timezone.utc) + timedelta(minutes=30)},
        AUTH_CRYPT_KEY,
        algorithm="HS256"
    )
    return jsonify(token=token)

NGROK_TOKEN = os.getenv('NGROK_AUTHTOKEN')
ngrok.set_auth_token(NGROK_TOKEN)
def force_kill_ngrok():
    try:
        if platform.system() == "Windows":
            os.system("taskkill /f /im ngrok.exe >nul 2>&1")
        else:
            os.system("killall -9 ngrok >/dev/null 2>&1")
    except:
        pass

force_kill_ngrok()

listener = ngrok.connect(5000)
print(f"Ngrok URL: {listener.public_url}")

if __name__ == "__main__":
    app.run(port=5000)
