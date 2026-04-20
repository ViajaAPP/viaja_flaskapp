from flask import Blueprint, current_app, jsonify
from app.services.supabase_service import supabase

health_bp = Blueprint('health', __name__)

@health_bp.route('/', methods=['GET'])
def health_check():
    try:
        supabase.table("user").select("*").limit(1).execute()
    except Exception as e:
        current_app.logger.exception(e)
        return jsonify({"status": "error", "details": "Database connection failed"}), 500
    return jsonify({"status": "ok"}), 200