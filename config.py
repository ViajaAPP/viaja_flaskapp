import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    AUTH_CRYPT_KEY = os.getenv('AUTH_CRYPT_KEY')
    DADOS_CRYPT_KEY = os.getenv('DADOS_CRYPT_KEY')
    NGROK_AUTHTOKEN = os.getenv('NGROK_AUTHTOKEN')
    CIDADESBR_API_URL = os.getenv('CIDADESBR_API_URL', 'https://cidadesbr-api.onrender.com')
    APP_URL = os.getenv('APP_URL', 'http://localhost:4200')
    PHOTON_URL = os.getenv('PHOTON_URL', 'https://photon.komoot.io')
    SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = os.getenv('SMTP_PORT', '587')
    SMTP_USER = os.getenv('SMTP_USER')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
    SMTP_FROM = os.getenv('SMTP_FROM', os.getenv('SMTP_USER'))

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    
config_dict = {
    "development": DevelopmentConfig,
    "production": ProductionConfig
}