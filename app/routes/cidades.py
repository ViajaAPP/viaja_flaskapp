from flask import Blueprint, request, jsonify
from app.services import cidades_service
from app.utils.auth import token_opcional
from app.utils.limite import limite_para_visitante

cidades_bp = Blueprint('cidades', __name__)

@cidades_bp.route('/busca', methods=['GET'])
@token_opcional
@limite_para_visitante()
def buscar_cidades(current_user):
    texto = (request.args.get('q') or '').strip()
    if not texto:
        return jsonify([]), 200
    cidades = cidades_service.buscar_cidades(texto, request.args.get('uf'))
    return jsonify([{"name": cidade['name'], "uf": cidade['state']} for cidade in cidades]), 200
