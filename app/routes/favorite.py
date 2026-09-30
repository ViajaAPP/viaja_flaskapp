from flask import Blueprint, current_app, jsonify
from app.services.supabase_service import supabase
from app.services import tour_service
from app.utils.auth import token_required

favorite_bp = Blueprint('favorite', __name__)

@favorite_bp.route('/<int:tour_id>', methods=['POST'])
@token_required
def add_favorite(current_user, tour_id):
    tour = tour_service.find_tour(tour_id)
    if not tour or not tour['published']:
        return jsonify({"error": "Tour não encontrado"}), 404
    try:
        supabase.table("favorite_tour").upsert(
            {"user_id": current_user['user_id'], "tour_id": tour_id},
            on_conflict="user_id,tour_id",
            ignore_duplicates=True
        ).execute()
        return jsonify({"favorite": True}), 200
    except Exception as e:
        current_app.logger.error(f"Erro ao favoritar tour: {e}")
        return jsonify({"error": "Erro ao favoritar tour"}), 500

@favorite_bp.route('/<int:tour_id>', methods=['DELETE'])
@token_required
def remove_favorite(current_user, tour_id):
    try:
        supabase.table("favorite_tour").delete().eq("user_id", current_user['user_id']).eq("tour_id", tour_id).execute()
        return jsonify({"favorite": False}), 200
    except Exception as e:
        current_app.logger.error(f"Erro ao desfavoritar tour: {e}")
        return jsonify({"error": "Erro ao desfavoritar tour"}), 500
