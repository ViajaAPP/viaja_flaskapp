import math
import time
from typing import Optional
from urllib.parse import quote

import requests
from flask import current_app

CACHE_SEGUNDOS = 24 * 60 * 60
TEMPO_LIMITE_SEGUNDOS = 60

_cache: dict[str, tuple[float, object]] = {}


def _consultar(caminho: str, params: Optional[dict] = None):
    chave = caminho + "?" + "&".join(f"{k}={v}" for k, v in sorted((params or {}).items()))
    agora = time.time()
    guardado = _cache.get(chave)
    if guardado and agora - guardado[0] < CACHE_SEGUNDOS:
        return guardado[1]

    url = current_app.config["CIDADESBR_API_URL"].rstrip("/") + caminho
    try:
        resposta = requests.get(url, params=params, timeout=TEMPO_LIMITE_SEGUNDOS)
    except requests.RequestException as e:
        current_app.logger.error(f"Erro na CidadesBR-API: {e}")
        return None

    if resposta.status_code == 404:
        _cache[chave] = (agora, None)
        return None
    if resposta.status_code != 200:
        current_app.logger.error(f"CidadesBR-API respondeu {resposta.status_code} em {caminho}")
        return None

    dados = resposta.json()
    _cache[chave] = (agora, dados)
    return dados


def buscar_cidades(texto: str, uf: Optional[str] = None, limite: int = 8) -> list[dict]:
    params = {"q": texto, "limit": limite}
    if uf:
        params["uf"] = uf.upper()
    dados = _consultar("/cidades/busca", params)
    return dados if isinstance(dados, list) else []


def coordenadas_da_cidade(nome: str, uf: str) -> Optional[tuple[float, float]]:
    if not nome or not uf:
        return None
    dados = _consultar(f"/estados/{uf.upper()}/cidades/{quote(nome.strip())}")
    if not isinstance(dados, dict) or "lat" not in dados:
        return None
    return dados["lat"], dados["lon"]


def distancia_km(origem: tuple[float, float], destino: tuple[float, float]) -> float:
    lat1, lon1 = map(math.radians, origem)
    lat2, lon2 = map(math.radians, destino)
    a = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))
