import time
from typing import Optional
import requests
from flask import current_app

CACHE_SEGUNDOS = 24 * 60 * 60
TEMPO_LIMITE_SEGUNDOS = 8
CENTRO_PADRAO = (-23.96, -46.33)

UF_POR_ESTADO = {
    "Acre": "AC", "Alagoas": "AL", "Amapá": "AP", "Amazonas": "AM", "Bahia": "BA", "Ceará": "CE",
    "Distrito Federal": "DF", "Espírito Santo": "ES", "Goiás": "GO", "Maranhão": "MA",
    "Mato Grosso": "MT", "Mato Grosso do Sul": "MS", "Minas Gerais": "MG", "Pará": "PA",
    "Paraíba": "PB", "Paraná": "PR", "Pernambuco": "PE", "Piauí": "PI", "Rio de Janeiro": "RJ",
    "Rio Grande do Norte": "RN", "Rio Grande do Sul": "RS", "Rondônia": "RO", "Roraima": "RR",
    "Santa Catarina": "SC", "São Paulo": "SP", "Sergipe": "SE", "Tocantins": "TO",
}

_cache: dict[str, tuple[float, object]] = {}

def _consultar(caminho: str, params: dict):
    chave = caminho + "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    agora = time.time()
    guardado = _cache.get(chave)
    if guardado and agora - guardado[0] < CACHE_SEGUNDOS:
        return guardado[1]

    url = current_app.config["PHOTON_URL"].rstrip("/") + caminho
    resposta = requests.get(url, params=params, timeout=TEMPO_LIMITE_SEGUNDOS, headers={"User-Agent": "Viaja/1.0"})
    resposta.raise_for_status()
    dados = resposta.json()
    _cache[chave] = (agora, dados)
    return dados

def _local(feature: dict) -> Optional[dict]:
    propriedades = feature.get("properties") or {}
    if propriedades.get("countrycode") != "BR":
        return None
    lon, lat = feature["geometry"]["coordinates"]
    cep = "".join(c for c in (propriedades.get("postcode") or "") if c.isdigit())
    return {
        "nome": propriedades.get("name") or propriedades.get("street") or "",
        "rua": propriedades.get("street") or "",
        "numero": propriedades.get("housenumber") or "",
        "bairro": propriedades.get("district") or propriedades.get("locality") or "",
        "cidade": propriedades.get("city") or propriedades.get("county") or "",
        "uf": UF_POR_ESTADO.get(propriedades.get("state") or "", ""),
        "cep": cep if len(cep) == 8 else "",
        "lat": lat,
        "lon": lon,
    }

def buscar(texto: str, perto: Optional[tuple[float, float]] = None, limite: int = 6, so_pontos: bool = False) -> list[dict]:
    lat, lon = perto or CENTRO_PADRAO
    dados = _consultar("/api/", {"q": texto, "limit": limite * 3, "lat": lat, "lon": lon})
    features = dados.get("features") or []
    if so_pontos:
        features = [f for f in features if (f.get("properties") or {}).get("osm_key") not in ("place", "boundary")]
    locais, vistos = [], set()
    for local in map(_local, features):
        chave = (local or {}).get("nome", "").lower(), (local or {}).get("rua", "").lower(), (local or {}).get("cidade", "").lower()
        if local and chave not in vistos:
            vistos.add(chave)
            locais.append(local)
    return locais[:limite]

def endereco_do_ponto(lat: float, lon: float) -> Optional[dict]:
    dados = _consultar("/reverse", {"lat": round(lat, 6), "lon": round(lon, 6), "limit": 5, "radius": 1})
    locais = [local for local in map(_local, dados.get("features") or []) if local]
    if not locais:
        return None
    endereco = next((local for local in locais if local["rua"]), locais[0])
    cep = endereco["cep"] or next((local["cep"] for local in locais if local["cep"]), "")
    if not cep:
        cep = next((digitos for digitos in ("".join(c for c in local["nome"] if c.isdigit()) for local in locais) if len(digitos) == 8), "")
    nome = endereco["nome"] if not endereco["nome"].replace("-", "").isdigit() else endereco["rua"]
    return {**endereco, "nome": nome, "cep": cep, "lat": lat, "lon": lon}
