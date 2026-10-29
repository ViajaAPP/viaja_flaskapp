from datetime import datetime, timedelta, timezone
from app.services import supabase_service, cidades_service, review_service

FUSO = timezone(timedelta(hours=-3))
RAIO_KM = 20
FOLGA = timedelta(minutes=45)
DURACAO_PADRAO = timedelta(hours=2)
MAXIMO_POR_DIA = 4

def _data(texto):
    return datetime.fromisoformat(texto.replace('Z', '+00:00'))

def _ponto(endereco, cidade_padrao):
    if endereco.get("lat") is not None and endereco.get("lon") is not None:
        return endereco["lat"], endereco["lon"]
    return cidades_service.coordenadas_da_cidade(endereco.get("city"), endereco.get("uf")) or cidade_padrao

def _nota_ajustada(media, quantidade, media_geral=4.2, peso=3):
    return ((media or 0) * quantidade + media_geral * peso) / (quantidade + peso)

def _passeios(centro, desde, ate):
    passeios = supabase_service.supabase.table("tour") \
        .select("id, title, photo, price, meeting_point, estimated_duration_minutes, address(city, uf, lat, lon), tour_instance(id, start_time, status, registration)") \
        .eq("published", True).execute().data or []
    notas = review_service.summary_by_tour([p["id"] for p in passeios])
    itens = []
    for passeio in passeios:
        endereco = passeio.get("address") or {}
        ponto = _ponto(endereco, None)
        if not ponto or cidades_service.distancia_km(centro, ponto) > RAIO_KM:
            continue
        nota = notas.get(passeio["id"]) or {}
        duracao = timedelta(minutes=passeio["estimated_duration_minutes"]) if passeio.get("estimated_duration_minutes") else DURACAO_PADRAO
        for instancia in passeio.get("tour_instance") or []:
            inicio = _data(instancia["start_time"])
            if instancia["status"] != "SCHEDULED" or instancia.get("registration") == "CLOSED" or not (desde <= inicio < ate):
                continue
            itens.append({
                "tipo": "passeio", "id": passeio["id"], "instancia_id": instancia["id"], "titulo": passeio["title"],
                "foto": passeio["photo"], "preco": passeio["price"], "nota": nota.get("average"), "avaliacoes": nota.get("count", 0),
                "lugar": passeio.get("meeting_point") or endereco.get("city"), "lat": ponto[0], "lon": ponto[1],
                "inicio": inicio, "fim": inicio + duracao,
                "pontos": _nota_ajustada(nota.get("average"), nota.get("count", 0)),
            })
    return itens

def _eventos(centro, desde, ate):
    eventos = supabase_service.supabase.table("event") \
        .select("id, title, photo, price, place_name, start_time, end_time, address(city, uf, lat, lon)") \
        .eq("status", "PUBLISHED").gte("start_time", desde.isoformat()).lt("start_time", ate.isoformat()).execute().data or []
    ids = [e["id"] for e in eventos]
    presencas = {}
    if ids:
        for p in supabase_service.supabase.table("event_attendance").select("event_id").in_("event_id", ids).execute().data or []:
            presencas[p["event_id"]] = presencas.get(p["event_id"], 0) + 1
    itens = []
    for evento in eventos:
        endereco = evento.get("address") or {}
        ponto = _ponto(endereco, None)
        if not ponto or cidades_service.distancia_km(centro, ponto) > RAIO_KM:
            continue
        inicio = _data(evento["start_time"])
        itens.append({
            "tipo": "evento", "id": evento["id"], "instancia_id": None, "titulo": evento["title"], "foto": evento["photo"],
            "preco": evento["price"], "nota": None, "avaliacoes": 0, "vao": presencas.get(evento["id"], 0),
            "lugar": evento.get("place_name") or endereco.get("city"), "lat": ponto[0], "lon": ponto[1],
            "inicio": inicio, "fim": _data(evento["end_time"]) if evento.get("end_time") else inicio + DURACAO_PADRAO,
            "pontos": 4.3 + min(presencas.get(evento["id"], 0), 10) * 0.05,
        })
    return itens

def _bate(item, escolhidos):
    return any(item["inicio"] < outro["fim"] + FOLGA and outro["inicio"] < item["fim"] + FOLGA for outro in escolhidos)

def _montar_dia(candidatos):
    escolhidos = []
    for item in sorted(candidatos, key=lambda c: -c["pontos"]):
        if len(escolhidos) >= MAXIMO_POR_DIA:
            break
        if any(e["tipo"] == item["tipo"] and e["id"] == item["id"] for e in escolhidos) or _bate(item, escolhidos):
            continue
        escolhidos.append(item)
    escolhidos.sort(key=lambda c: c["inicio"])
    anterior = None
    for item in escolhidos:
        item["km_do_anterior"] = round(cidades_service.distancia_km((anterior["lat"], anterior["lon"]), (item["lat"], item["lon"])), 1) if anterior else None
        anterior = item
    return [{**{k: v for k, v in item.items() if k != "pontos"}, "inicio": item["inicio"].isoformat(), "fim": item["fim"].isoformat()} for item in escolhidos]

def montar(cidade, uf, primeiro_dia, dias):
    centro = cidades_service.coordenadas_da_cidade(cidade, uf)
    if not centro:
        return None
    inicio = datetime.combine(primeiro_dia, datetime.min.time(), FUSO)
    fim = inicio + timedelta(days=dias)
    candidatos = _passeios(centro, inicio, fim) + _eventos(centro, inicio, fim)
    roteiro = []
    for n in range(dias):
        dia = inicio + timedelta(days=n)
        do_dia = [c for c in candidatos if dia <= c["inicio"] < dia + timedelta(days=1)]
        roteiro.append({"data": dia.date().isoformat(), "itens": _montar_dia(do_dia)})
    return {"cidade": cidade, "uf": uf, "dias": roteiro}
