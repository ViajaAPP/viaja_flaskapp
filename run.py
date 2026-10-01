import os
import sys
from app import create_app
from pyngrok import ngrok, conf
from dotenv import load_dotenv

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
    ws_url = public_url.replace("https://", "wss://").replace("http://", "ws://")
    atualiza_env("PUBLIC_URL_WS", ws_url)
    print(f" * Chat disponível em: {ws_url}/ws")

app = create_app()

if __name__ == "__main__":
    is_local = "--local" in sys.argv
    is_flask_reloader = os.environ.get("WERKZEUG_RUN_MAIN") == "true"

    if not is_flask_reloader:
        if is_local:
            print(" * Chat local em ws://localhost:5000/ws")
        elif os.environ.get("NGROK_API_TOKEN"):
            start_ngrok_api(conf.PyngrokConfig(auth_token=os.environ.get("NGROK_API_TOKEN")))
        else:
            print(" * Erro: Token do ngrok em falta no ficheiro .env")
            sys.exit(1)

    print(" * Iniciando Servidor Flask...")
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=True)
