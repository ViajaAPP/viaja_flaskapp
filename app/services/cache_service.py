import json
import os
import threading
import time
from functools import wraps

TEMPO_PADRAO = 60

_memoria: dict[str, tuple[float, str]] = {}
_versoes: dict[str, int] = {}
_contagens: dict[str, tuple[float, int]] = {}
_trava = threading.Lock()
_redis = None
_redis_tentado = False

def _cliente():
    global _redis, _redis_tentado
    if _redis_tentado:
        return _redis
    _redis_tentado = True
    url = os.getenv("REDIS_URL")
    if not url:
        return None
    try:
        import redis
        cliente = redis.Redis.from_url(url, socket_timeout=0.5, socket_connect_timeout=0.5)
        cliente.ping()
        _redis = cliente
    except Exception:
        _redis = None
    return _redis

def _versao(espaco):
    cliente = _cliente()
    if cliente:
        try:
            return int(cliente.get(f"viaja:versao:{espaco}") or 0)
        except Exception:
            pass
    return _versoes.get(espaco, 0)

def invalidar(espaco):
    cliente = _cliente()
    if cliente:
        try:
            cliente.incr(f"viaja:versao:{espaco}")
        except Exception:
            pass
    with _trava:
        _versoes[espaco] = _versoes.get(espaco, 0) + 1

def _ler(chave):
    cliente = _cliente()
    if cliente:
        try:
            valor = cliente.get(chave)
            return json.loads(valor) if valor is not None else None
        except Exception:
            pass
    guardado = _memoria.get(chave)
    if guardado and guardado[0] > time.time():
        return json.loads(guardado[1])
    return None

def _gravar(chave, valor, segundos):
    texto = json.dumps(valor, default=str)
    cliente = _cliente()
    if cliente:
        try:
            cliente.set(chave, texto, ex=segundos)
            return
        except Exception:
            pass
    with _trava:
        if len(_memoria) > 2000:
            _memoria.clear()
        _memoria[chave] = (time.time() + segundos, texto)

def lembrar(espaco, segundos=TEMPO_PADRAO):
    def decorador(funcao):
        @wraps(funcao)
        def envolvida(*args, **kwargs):
            chave = f"viaja:{espaco}:{_versao(espaco)}:{funcao.__module__}.{funcao.__name__}:{json.dumps([args, kwargs], default=str, sort_keys=True)}"
            valor = _ler(chave)
            if valor is not None:
                return valor
            valor = funcao(*args, **kwargs)
            _gravar(chave, valor, segundos)
            return valor
        return envolvida
    return decorador

def contar(chave, segundos):
    cliente = _cliente()
    if cliente:
        try:
            total = cliente.incr(f"viaja:conta:{chave}")
            if total == 1:
                cliente.expire(f"viaja:conta:{chave}", segundos)
            return total
        except Exception:
            pass
    agora = time.time()
    with _trava:
        fim, total = _contagens.get(chave, (0, 0))
        if fim <= agora:
            fim, total = agora + segundos, 0
        if len(_contagens) > 5000:
            _contagens.clear()
        _contagens[chave] = (fim, total + 1)
        return total + 1
