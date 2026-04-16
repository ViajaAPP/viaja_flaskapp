import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from supabase import create_client, Client

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')

supabase: Client = create_client(url, key)
app = Flask(__name__)

@app.route('/')
def hello():
    # verificar conexão com o supabase
    try:
        response = supabase.rpc("health_check").execute()
        if response.data == 1:
            return jsonify({"database": "online"})
        else:
            return jsonify({"database": "offline"})
    except Exception as e:
        return f"Erro ao conectar com o Supabase: {e}"

if __name__ == "__main__":
    # o host deve ser '0.0.0.0' para que o app seja acessível fora do container
    app.run(host='0.0.0.0', port=5000, debug=True)
