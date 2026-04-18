from supabase import create_client, Client
from flask import current_app

supabase: Client = None

def init_supabase(app):
    global supabase
    url = app.config['SUPABASE_URL']
    key = app.config['SUPABASE_KEY']
    
    if not supabase:
        supabase = create_client(url, key)
    return supabase