import os
import sys
import threading
from app import create_app
from pyngrok import ngrok, conf
from dotenv import load_dotenv
from sockets import *

load_dotenv()

def atualiza_env(key: str, value: str):
    env_path = ".env"
    new_line = f"{key}={value}\n"
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()
        with open(env_path, "w") as f:
            found = False
            for line in lines:
                if line.startswith(f"{key}="):
                    f.write(new_line)
                    found = True
                else:
                    f.write(line)
            if not found:
                f.write(new_line)

def start_ngrok_api(config):
    public_url = ngrok.connect(5000, name="flask-api", pyngrok_config=config).public_url
    print(f" * API Flask disponível em: {public_url}")

def start_ngrok_ws(config):
    public_url = ngrok.connect(8765, "tcp", name="socket-server", pyngrok_config=config).public_url
    print(f" * WebSocket disponível em: {public_url}")
    
    # padroniza o protocolo para ws://
    ws_url = public_url.replace("tcp://", "ws://").replace("http://", "ws://").replace("https://", "ws://")
    atualiza_env("PUBLIC_URL_WS", ws_url)
    
    # executa o servidor socket (bloqueante) dentro desta thread dedicada
    start_server_socket()

app = create_app()

if __name__ == "__main__":
    only_api = "--api" in sys.argv
    only_ws = "--ws" in sys.argv

    if only_api and only_ws:
        print(" * Erro: Não pode iniciar ambos os serviços com os argumentos --api e --ws.")
        sys.exit(1)

    NGROK_WS_TOKEN = os.environ.get("NGROK_WS_TOKEN")
    NGROK_API_TOKEN = os.environ.get("NGROK_API_TOKEN")

    is_flask_reloader = os.environ.get("WERKZEUG_RUN_MAIN") == "true"

    if not is_flask_reloader:
        if NGROK_WS_TOKEN and NGROK_API_TOKEN:
            config_api = conf.PyngrokConfig(auth_token=NGROK_API_TOKEN)
            config_ws = conf.PyngrokConfig(auth_token=NGROK_WS_TOKEN)

            # inicia o WebSocket apenas se não foi pedida "apenas a api"
            if not only_api:
                t_ws = threading.Thread(target=start_ngrok_ws, args=(config_ws,), daemon=True)
                t_ws.start()
                print(" * Serviço WebSocket iniciado em background.")

            #iInicia o túnel da API se não foi pedido "apenas o ws"
            if not only_ws:
                start_ngrok_api(config_api)
        else:
            print(" * Erro: Tokens do ngrok em falta no ficheiro .env")
            sys.exit(1)

    # se houver alterações de código, apenas esta parte reinicia
    if not only_ws:
        print(" * Iniciando Servidor Flask...")
        app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=True)