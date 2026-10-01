import math
import unicodedata
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Optional
from app.services.supabase_service import supabase
from app.services import cidades_service, local_service, review_service, tour_service
from app.services.cache_service import lembrar

FUSO = timezone(timedelta(hours=-3))
RAIO_PADRAO_KM = 50

def _sem_acento(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()

@lembrar("passeios")
def _passeios_publicados():
    return supabase.table("tour") \
        .select("id, title, description, price, photo, created_by_id, address(city, uf, lat, lon), tour_instance(id, start_time, status, registration, max_capacity)") \
        .eq("published", True).execute().data or []

def _ponto_do_passeio(passeio, coordenadas_por_cidade):
    endereco = passeio.get("address") or {}
    if endereco.get("lat") is not None and endereco.get("lon") is not None:
        return endereco["lat"], endereco["lon"]
    chave = (endereco.get("city"), endereco.get("uf"))
    if chave not in coordenadas_por_cidade:
        coordenadas_por_cidade[chave] = cidades_service.coordenadas_da_cidade(*chave)
    return coordenadas_por_cidade[chave]

def _proximas_instancias(passeio):
    agora = datetime.now(timezone.utc)
    futuras = [
        (datetime.fromisoformat(i["start_time"].replace("Z", "+00:00")), i)
        for i in passeio.get("tour_instance") or [] if i["status"] == "SCHEDULED"
    ]
    return sorted([(inicio, i) for inicio, i in futuras if inicio > agora], key=lambda par: par[0])

def _proximas_saidas(passeio):
    return [inicio for inicio, _ in _proximas_instancias(passeio)]

def _confirmados_por_instancia(passeios):
    ids = [i["id"] for p in passeios for _, i in _proximas_instancias(p)[:1]]
    if not ids:
        return {}
    aceitos = supabase.table("tour_request").select("tour_instance_id").in_("tour_instance_id", ids).eq("status", "ACCEPTED").execute().data or []
    return Counter(a["tour_instance_id"] for a in aceitos)

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

def _vagas_livres(proximas, confirmados):
    if not proximas:
        return None
    instancia = proximas[0][1]
    if instancia["registration"] == "FULL":
        return 0
    return max(instancia["max_capacity"] - confirmados.get(instancia["id"], 0), 0)

def _historico(user_id):
    favoritos = tour_service.list_favorite_tour_ids(user_id)
    pedidos = supabase.table("tour_request").select("status, tour_instance(tour_id)").eq("requester_id", user_id).execute().data or []
    reservados = {(p.get("tour_instance") or {}).get("tour_id") for p in pedidos if p["status"] in ("PENDING", "ACCEPTED")}
    pedidos_ids = {(p.get("tour_instance") or {}).get("tour_id") for p in pedidos}
    avaliados = {r["tour_id"] for r in supabase.table("tour_review").select("tour_id").eq("user_id", user_id).execute().data or []}
    return favoritos | pedidos_ids | avaliados, reservados - {None}

def _nota_ajustada(media, quantidade, media_geral=4.2, peso=3):
    return ((media or 0) * quantidade + media_geral * peso) / (quantidade + peso)

def _ordenar_para_voce(user_id, resultados, centro):
    interesses, reservados = _historico(user_id)
    do_interesse = [r for r in resultados if r["id"] in interesses]
    cidades = Counter((r["city"], r["uf"]) for r in do_interesse)
    maior_cidade = max(cidades.values()) if cidades else 1
    precos = [r["price"] for r in do_interesse]
    preco_medio = sum(precos) / len(precos) if precos else None
    maior_popularidade = max((r["likes"] + r["searches"] for r in resultados), default=0) or 1
    agora = datetime.now(timezone.utc)

    def pontos(r):
        qualidade = _nota_ajustada(r["rating"], r["reviewCount"]) / 5
        popularidade = math.log1p(r["likes"] + r["searches"]) / math.log1p(maior_popularidade)
        afinidade = cidades.get((r["city"], r["uf"]), 0) / maior_cidade if cidades else 0
        preco = 1 - min(abs(r["price"] - preco_medio) / max(preco_medio, 50), 1) if preco_medio is not None else 0
        em_breve = 1 if r["nextDate"] and datetime.fromisoformat(r["nextDate"]) - agora < timedelta(days=14) else 0
        perto = 1 - min(r["distance_km"], 100) / 100 if centro and r["distance_km"] is not None else 0
        ja_reservado = -3 if r["id"] in reservados else 0
        return 2 * qualidade + popularidade + 1.5 * afinidade + preco + 0.8 * em_breve + perto + ja_reservado

    return sorted(resultados, key=pontos, reverse=True)

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

@lembrar("passeios", segundos=300)
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

def buscar_passeios(user_id: Optional[int], centro: Optional[tuple[float, float]] = None, raio_km: Optional[float] = None,
                    texto: str = "", preco_max: Optional[float] = None, gratuito: bool = False,
                    quando: Optional[str] = None, nota_min: Optional[float] = None, ordem: str = "relevancia") -> list[dict]:
    passeios = _passeios_publicados()
    guias = tour_service.find_users({p["created_by_id"] for p in passeios})
    favoritos = tour_service.list_favorite_tour_ids(user_id) if user_id else set()
    curtidas = tour_service.count_favorites_by_tour()
    pedidos = tour_service.count_requests_by_tour()
    avaliacoes = review_service.summary_by_tour()
    janela = _janela(quando)
    confirmados = _confirmados_por_instancia(passeios)
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
            "guideId": passeio["created_by_id"],
            "price": preco,
            "city": endereco.get("city"),
            "uf": endereco.get("uf"),
            "distance_km": round(distancia, 1) if distancia is not None else None,
            "rating": nota.get("average"),
            "reviewCount": nota.get("count", 0),
            "likes": curtidas.get(passeio["id"], 0),
            "searches": pedidos.get(passeio["id"], 0),
            "nextDate": saidas[0].isoformat() if saidas else None,
            "spotsLeft": _vagas_livres(_proximas_instancias(passeio), confirmados),
            "favorite": passeio["id"] in favoritos,
        })

    chaves = {
        "perto": lambda r: (r["distance_km"] if r["distance_km"] is not None else 1e9),
        "nota": lambda r: (-(r["rating"] or 0), -r["reviewCount"]),
        "curtidos": lambda r: -r["likes"],
        "procurados": lambda r: -r["searches"],
        "preco": lambda r: r["price"],
    }
    if ordem == "para_voce" and user_id:
        return _ordenar_para_voce(user_id, resultados, centro)
    chave = chaves.get(ordem) or (lambda r: (
        r["nextDate"] is None,
        r["distance_km"] if r["distance_km"] is not None else 0,
        -(r["rating"] or 0),
    ))
    resultados.sort(key=chave)
    return resultados
