from flask import Blueprint, current_app, request, jsonify
from pydantic import ValidationError
from app.models.user_models import UserCreate # Seu DTO
from app.services.cnpj_service import buscar_dados_cnpj
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from app.services.supabase_service import supabase

health_bp = Blueprint('health', __name__)

@health_bp.route('/', methods=['GET'])
def health_check():
    # db status
    try:
        supabase.table("user").select("*").limit(1).execute()
    except Exception as e:
        current_app.logger.exception(e)
        return jsonify({"status": "error", "details": "Database connection failed"}), 500
    return jsonify({"status": "ok"}), 200