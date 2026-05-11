import os
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
    # tem que executar nele a função start_server_socket() do sockets.py
    public_url = ngrok.connect(8765, "tcp", name="socket-server", pyngrok_config=config).public_url
    print(f" * WebSocket disponível em: {public_url}")
    atualiza_env("PUBLIC_URL_WS", public_url.replace("tcp://", "ws://").replace("http://", "ws://").replace("https://", "ws://"))
    start_server_socket()

app = create_app()

if __name__ == "__main__":
    # startar socket em uma url ngrok e o flask app em outra url ngrok, cada um em uma thread diferente, com pooling enabled
    NGROK_WS_TOKEN = os.environ.get("NGROK_WS_TOKEN")
    NGROK_API_TOKEN = os.environ.get("NGROK_API_TOKEN")

    if NGROK_WS_TOKEN and NGROK_API_TOKEN:
        config_api = conf.PyngrokConfig(auth_token=NGROK_API_TOKEN)
        config_ws = conf.PyngrokConfig(auth_token=NGROK_WS_TOKEN)
        
        # WEBSOCKET: Precisa de thread se start_server_socket() for bloqueante
        t_ws = threading.Thread(target=start_ngrok_ws, args=(config_ws,), daemon=True)
        t_ws.start()

        # API: É melhor rodar fora de thread para garantir que a URL apareça 
        start_ngrok_api(config_api)

        print(" * Iniciando Servidor Flask...")
        app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)