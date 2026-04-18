import os
import platform
from flask import jsonify
from app import create_app
from pyngrok import ngrok
from dotenv import load_dotenv

load_dotenv()

def force_kill_ngrok():
    try:
        if platform.system() == "Windows":
            os.system("taskkill /f /im ngrok.exe >nul 2>&1")
        else:
            os.system("killall -9 ngrok >/dev/null 2>&1")
    except:
        pass


app = create_app()

if __name__ == "__main__":
    NGROK_TOKEN = os.environ.get("NGROK_AUTHTOKEN")
    if NGROK_TOKEN:
        force_kill_ngrok()
        ngrok.set_auth_token(NGROK_TOKEN)
        public_url = ngrok.connect(5000).public_url
        print(f" * Ngrok tunnel disponível em: {public_url}")
    
    app.run(port=5000, debug=True)