import os
from app import create_app
from pyngrok import ngrok, conf
from dotenv import load_dotenv
from sockets import *

load_dotenv()

app = create_app()

if __name__ == "__main__":
    # startar socket em uma url ngrok e o flask app em outra url ngrok, cada um em uma thread diferente
    NGROK_WS_TOKEN = os.environ.get("NGROK_WS_TOKEN")
    NGROK_API_TOKEN = os.environ.get("NGROK_API_TOKEN")
    if NGROK_WS_TOKEN and NGROK_API_TOKEN:
        config_api = conf.PyngrokConfig(auth_token=NGROK_API_TOKEN)
        public_url_api = ngrok.connect(5000, pyngrok_config=config_api).public_url
        print(f" * API Flask disponível em: {public_url_api}")

        config_ws = conf.PyngrokConfig(auth_token=NGROK_WS_TOKEN)
        public_url_ws = ngrok.connect(8765, "tcp", pyngrok_config=config_ws).public_url
        print(f" * WebSocket disponível em: {public_url_ws}")
    