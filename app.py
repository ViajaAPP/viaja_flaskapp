import os
from dotenv import load_dotenv
from flask import Flask
from supabase import create_client, Client

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')

supabase: Client = create_client(url, key)
app = Flask(__name__)

@app.route('/')
def hello():
    return "Hello World!"

if __name__ == "__main__":
    # o host deve ser '0.0.0.0' para que o app seja acessível fora do container
    app.run(host='0.0.0.0', port=5000, debug=True)
