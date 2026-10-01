from functools import wraps
from flask import jsonify, request
from app.services import cache_service

def _origem():
    encaminhado = request.headers.get("X-Forwarded-For", "")
    return encaminhado.split(",")[0].strip() or request.remote_addr or "desconhecido"

def limite_para_visitante(por_minuto=60):
    def decorador(f):
        @wraps(f)
        def decorated(current_user, *args, **kwargs):
            if current_user is None and cache_service.contar(f"visitante:{_origem()}", 60) > por_minuto:
                return jsonify({"error": "Muitas buscas seguidas. Espere um pouquinho e tente de novo."}), 429
            return f(current_user, *args, **kwargs)
        return decorated
    return decorador
