from flask import Blueprint, request, jsonify
from app.services import cidades_service
from app.utils.auth import token_required

cidades_bp = Blueprint('cidades', __name__)

@cidades_bp.route('/busca', methods=['GET'])
@token_required
def buscar_cidades(current_user):
    texto = (request.args.get('q') or '').strip()
    if len(texto) < 2:
        return jsonify([]), 200
    cidades = cidades_service.buscar_cidades(texto, request.args.get('uf'))
    return jsonify([{"name": cidade['name'], "uf": cidade['state']} for cidade in cidades]), 200
