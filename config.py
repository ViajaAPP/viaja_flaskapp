import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    AUTH_CRYPT_KEY = os.getenv('AUTH_CRYPT_KEY')
    NGROK_AUTHTOKEN = os.getenv('NGROK_AUTHTOKEN')
    CIDADESBR_API_URL = os.getenv('CIDADESBR_API_URL', 'https://cidadesbr-api.onrender.com')

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    
config_dict = {
    "development": DevelopmentConfig,
    "production": ProductionConfig
}