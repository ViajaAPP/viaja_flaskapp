import unicodedata
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Optional
from app.services.supabase_service import supabase
from app.services import cidades_service, local_service, review_service, tour_service

FUSO = timezone(timedelta(hours=-3))
RAIO_PADRAO_KM = 50

def _sem_acento(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()

def _passeios_publicados():
    return supabase.table("tour") \
        .select("id, title, description, price, photo, created_by_id, address(city, uf, lat, lon), tour_instance(start_time, status, registration)") \
        .eq("published", True).execute().data or []

def _ponto_do_passeio(passeio, coordenadas_por_cidade):
    endereco = passeio.get("address") or {}
    if endereco.get("lat") is not None and endereco.get("lon") is not None:
        return endereco["lat"], endereco["lon"]
    chave = (endereco.get("city"), endereco.get("uf"))
    if chave not in coordenadas_por_cidade:
        coordenadas_por_cidade[chave] = cidades_service.coordenadas_da_cidade(*chave)
    return coordenadas_por_cidade[chave]

def _proximas_saidas(passeio):
    agora = datetime.now(timezone.utc)
    saidas = []
    for instancia in passeio.get("tour_instance") or []:
        inicio = datetime.fromisoformat(instancia["start_time"].replace("Z", "+00:00"))
        if instancia["status"] == "SCHEDULED" and inicio > agora:
            saidas.append(inicio)
    return sorted(saidas)

def _janela(quando: Optional[str]):
    hoje = datetime.now(FUSO).replace(hour=0, minute=0, second=0, microsecond=0)
    if quando == "hoje":
        return hoje, hoje + timedelta(days=1)
    if quando == "fim-de-semana":
        sabado = hoje + timedelta(days=(5 - hoje.weekday()) % 7)
        if hoje.weekday() == 6:
            sabado = hoje - timedelta(days=1)
        return max(sabado, hoje), sabado + timedelta(days=2)
    if quando == "7-dias":
        return hoje, hoje + timedelta(days=7)
    return None

def sugestoes(texto: str, perto: Optional[tuple[float, float]] = None) -> dict:
    alvo = _sem_acento(texto)
    centro = perto or local_service.CENTRO_PADRAO
    com_passeios = {(d["nome"], d["uf"]): d for d in destinos_em_alta(limite=30)}
    encontradas = [
        {"name": d["nome"], "state": d["uf"], "lat": d["lat"], "lon": d["lon"], "passeios": d["passeios"]}
        for d in com_passeios.values() if alvo in _sem_acento(d["nome"])
    ]
    vistas = {(c["name"], c["state"]) for c in encontradas}
    encontradas += [c for c in cidades_service.buscar_cidades(texto, limite=40) if (c["name"], c["state"]) not in vistas]
    encontradas.sort(key=lambda cidade: (
        not _sem_acento(cidade["name"]).startswith(alvo),
        -cidade.get("passeios", 0),
        not cidade.get("isTourist"),
        not cidade.get("isCapital"),
        cidades_service.distancia_km(centro, (cidade["lat"], cidade["lon"])) if cidade.get("lat") is not None else 1e9,
    ))
    cidades = [{
        "tipo": "cidade", "nome": cidade["name"], "uf": cidade["state"],
        "ibge": cidade.get("ibgeCode"), "lat": cidade.get("lat"), "lon": cidade.get("lon"),
        "passeios": cidade.get("passeios", 0),
    } for cidade in encontradas[:5]]

    passeios = []
    for passeio in _passeios_publicados():
        titulo = _sem_acento(passeio["title"])
        casou = any(palavra.startswith(alvo) for palavra in titulo.split()) if len(alvo) < 3             else alvo in titulo or alvo in _sem_acento(passeio.get("description") or "")
        if casou:
            endereco = passeio.get("address") or {}
            passeios.append({
                "tipo": "passeio", "id": passeio["id"], "nome": passeio["title"],
                "cidade": endereco.get("city"), "uf": endereco.get("uf"), "foto": passeio.get("photo"),
            })
    passeios.sort(key=lambda p: (not _sem_acento(p["nome"]).startswith(alvo), p["nome"]))

    lugares = []
    try:
        for lugar in local_service.buscar(texto, perto, limite=4, so_pontos=True):
            lugares.append({"tipo": "lugar", **lugar})
    except Exception:
        pass

    return {"cidades": cidades, "passeios": passeios[:5], "lugares": lugares}

def destinos_em_alta(limite: int = 8) -> list[dict]:
    contagem = Counter()
    for passeio in _passeios_publicados():
        endereco = passeio.get("address") or {}
        if endereco.get("city") and endereco.get("uf"):
            contagem[(endereco["city"], endereco["uf"])] += 1
    destinos = []
    for (cidade, uf), quantidade in contagem.most_common(limite):
        ponto = cidades_service.coordenadas_da_cidade(cidade, uf)
        destinos.append({
            "tipo": "cidade", "nome": cidade, "uf": uf, "passeios": quantidade,
            "lat": ponto[0] if ponto else None, "lon": ponto[1] if ponto else None,
        })
    return destinos

def buscar_passeios(user_id: int, centro: Optional[tuple[float, float]] = None, raio_km: Optional[float] = None,
                    texto: str = "", preco_max: Optional[float] = None, gratuito: bool = False,
                    quando: Optional[str] = None, nota_min: Optional[float] = None, ordem: str = "relevancia") -> list[dict]:
    passeios = _passeios_publicados()
    guias = tour_service.find_users({p["created_by_id"] for p in passeios})
    favoritos = tour_service.list_favorite_tour_ids(user_id)
    curtidas = tour_service.count_favorites_by_tour()
    avaliacoes = review_service.summary_by_tour()
    janela = _janela(quando)
    alvo = _sem_acento(texto)
    raio = raio_km or RAIO_PADRAO_KM
    coordenadas_por_cidade = {}
    resultados = []

    for passeio in passeios:
        if alvo and alvo not in _sem_acento(passeio["title"]) and alvo not in _sem_acento(passeio.get("description") or ""):
            continue
        preco = passeio.get("price") or 0
        if gratuito and preco > 0:
            continue
        if preco_max is not None and preco > preco_max:
            continue
        nota = avaliacoes.get(passeio["id"]) or {}
        if nota_min and (nota.get("average") or 0) < nota_min:
            continue
        saidas = _proximas_saidas(passeio)
        if janela and not any(janela[0] <= saida.astimezone(FUSO) < janela[1] for saida in saidas):
            continue

        distancia = None
        if centro:
            ponto = _ponto_do_passeio(passeio, coordenadas_por_cidade)
            if not ponto:
                continue
            distancia = cidades_service.distancia_km(centro, ponto)
            if distancia > raio:
                continue

        endereco = passeio.get("address") or {}
        guia = guias.get(passeio["created_by_id"]) or {}
        resultados.append({
            "id": passeio["id"],
            "title": passeio["title"],
            "imageUrl": passeio.get("photo"),
            "guide": f"{guia.get('first_name', '')} {guia.get('last_name', '')}".strip(),
            "guideFoto": guia.get("photo"),
            "price": preco,
            "city": endereco.get("city"),
            "uf": endereco.get("uf"),
            "distance_km": round(distancia, 1) if distancia is not None else None,
            "rating": nota.get("average"),
            "reviewCount": nota.get("count", 0),
            "likes": curtidas.get(passeio["id"], 0),
            "nextDate": saidas[0].isoformat() if saidas else None,
            "favorite": passeio["id"] in favoritos,
        })

    chaves = {
        "perto": lambda r: (r["distance_km"] if r["distance_km"] is not None else 1e9),
        "nota": lambda r: (-(r["rating"] or 0), -r["reviewCount"]),
        "curtidos": lambda r: -r["likes"],
        "preco": lambda r: r["price"],
    }
    chave = chaves.get(ordem) or (lambda r: (
        r["nextDate"] is None,
        r["distance_km"] if r["distance_km"] is not None else 0,
        -(r["rating"] or 0),
    ))
    resultados.sort(key=chave)
    return resultados
