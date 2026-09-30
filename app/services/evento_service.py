from datetime import datetime, timedelta, timezone
from app.services.supabase_service import supabase
from app.services import aviso_service, cidades_service

FUSO = timezone(timedelta(hours=-3))
CAMPOS = "id, created_at, organizer_id, title, description, start_time, end_time, place_name, price, capacity, photo, photo_credit, status, review_note, reviewed_at, address(id, cep, uf, city, neighborhood, street, number, lat, lon)"
CAMPOS_QUE_PEDEM_ANALISE = ("start_time", "end_time", "address_id", "price", "title", "description", "photo")

def _data(texto):
    return datetime.fromisoformat(texto.replace('Z', '+00:00'))

def _quando(inicio):
    return _data(inicio).astimezone(FUSO).strftime('%d/%m às %H:%M')

def _pessoas(user_ids):
    if not user_ids:
        return {}
    dados = supabase.table("user").select("user_id, first_name, last_name, photo").in_("user_id", list(user_ids)).execute().data or []
    return {u["user_id"]: u for u in dados}

def _presencas(event_ids):
    if not event_ids:
        return []
    return supabase.table("event_attendance").select("event_id, user_id, created_at").in_("event_id", list(event_ids)).order("created_at").execute().data or []

def _serializar(evento, organizadores, presencas, user_id, centro=None, detalhado=False):
    endereco = evento.get("address") or {}
    do_evento = [p for p in presencas if p["event_id"] == evento["id"]]
    distancia = None
    if centro and endereco.get("lat") is not None:
        distancia = round(cidades_service.distancia_km(centro, (endereco["lat"], endereco["lon"])), 1)
    organizador = organizadores.get(evento["organizer_id"]) or {}
    item = {
        "id": evento["id"], "title": evento["title"], "photo": evento["photo"], "photo_credit": evento["photo_credit"],
        "start_time": evento["start_time"], "end_time": evento["end_time"], "price": evento["price"],
        "capacity": evento["capacity"], "place_name": evento["place_name"], "status": evento["status"],
        "city": endereco.get("city"), "uf": endereco.get("uf"), "distance_km": distancia,
        "going_count": len(do_evento), "going": any(p["user_id"] == user_id for p in do_evento),
        "organizer": {"user_id": organizador.get("user_id"), "first_name": organizador.get("first_name"), "photo": organizador.get("photo")},
        "is_owner": evento["organizer_id"] == user_id,
    }
    if detalhado:
        pessoas = _pessoas({p["user_id"] for p in do_evento[:12]})
        item.update({
            "description": evento["description"], "address": endereco,
            "review_note": evento["review_note"] if item["is_owner"] else None,
            "going_people": [
                {"first_name": (pessoas.get(p["user_id"]) or {}).get("first_name"), "photo": (pessoas.get(p["user_id"]) or {}).get("photo")}
                for p in do_evento[:12]
            ],
        })
    return item

def listar_publicados(user_id, centro=None, raio_km=None, gratuito=False, limite=None, ordem="data"):
    desde = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
    eventos = supabase.table("event").select(CAMPOS).eq("status", "PUBLISHED").gte("start_time", desde).order("start_time").execute().data or []
    if gratuito:
        eventos = [e for e in eventos if not e["price"]]
    organizadores = _pessoas({e["organizer_id"] for e in eventos})
    presencas = _presencas([e["id"] for e in eventos])
    itens = [_serializar(e, organizadores, presencas, user_id, centro) for e in eventos]
    if centro and raio_km:
        itens = [i for i in itens if i["distance_km"] is not None and i["distance_km"] <= raio_km]
    if ordem == "perto" and centro:
        itens.sort(key=lambda i: i["distance_km"] if i["distance_km"] is not None else 1e9)
    elif ordem == "populares":
        itens.sort(key=lambda i: -i["going_count"])
    return itens[:limite] if limite else itens

def buscar(evento_id):
    dados = supabase.table("event").select(CAMPOS).eq("id", evento_id).execute().data
    return dados[0] if dados else None

def detalhe(evento, user_id):
    organizadores = _pessoas({evento["organizer_id"]})
    return _serializar(evento, organizadores, _presencas([evento["id"]]), user_id, detalhado=True)

def listar_do_organizador(user_id):
    eventos = supabase.table("event").select(CAMPOS).eq("organizer_id", user_id).order("start_time", desc=True).execute().data or []
    organizadores = _pessoas({user_id})
    presencas = _presencas([e["id"] for e in eventos])
    return [{**_serializar(e, organizadores, presencas, user_id), "review_note": e["review_note"]} for e in eventos]

def listar_para_analise():
    eventos = supabase.table("event").select(CAMPOS).eq("status", "IN_REVIEW").order("created_at").execute().data or []
    organizadores = _pessoas({e["organizer_id"] for e in eventos})
    return [{**_serializar(e, organizadores, [], None, detalhado=False), "description": e["description"], "address": e.get("address")} for e in eventos]

def _admins():
    dados = supabase.table("user").select("user_id").eq("role", "ADMIN").execute().data or []
    return [u["user_id"] for u in dados]

def criar(organizador_id, campos):
    evento = supabase.table("event").insert({**campos, "organizer_id": organizador_id, "status": "IN_REVIEW"}).execute().data[0]
    aviso_service.criar(_admins(), "evento_para_analise", "Evento novo esperando análise", evento["title"], "/analise")
    return evento

def atualizar(evento, mudancas):
    if not mudancas:
        return evento
    publicado = evento["status"] == "PUBLISHED"
    pede_analise = any(campo in mudancas for campo in CAMPOS_QUE_PEDEM_ANALISE)
    if evento["status"] == "REJECTED" or (publicado and pede_analise):
        mudancas = {**mudancas, "status": "IN_REVIEW", "review_note": None}
        aviso_service.criar(_admins(), "evento_para_analise", "Evento alterado esperando análise", evento["title"], "/analise")
    supabase.table("event").update(mudancas).eq("id", evento["id"]).execute()
    if publicado and any(c in mudancas for c in ("start_time", "end_time", "address_id")):
        quem_vai = [p["user_id"] for p in _presencas([evento["id"]])]
        aviso_service.criar(quem_vai, "evento_mudou", "Um evento que você vai mudou",
                            f"{evento['title']}. Confira o novo dia, horário ou local.", f"/evento/{evento['id']}")
    return buscar(evento["id"])

def cancelar(evento):
    supabase.table("event").update({"status": "CANCELLED"}).eq("id", evento["id"]).execute()
    quem_vai = [p["user_id"] for p in _presencas([evento["id"]])]
    aviso_service.criar(quem_vai, "evento_cancelado", "Um evento que você ia foi cancelado",
                        f"{evento['title']}, {_quando(evento['start_time'])}.", f"/evento/{evento['id']}")

def analisar(evento, admin_id, aprovar, motivo=None):
    agora = datetime.now(timezone.utc).isoformat()
    supabase.table("event").update({
        "status": "PUBLISHED" if aprovar else "REJECTED",
        "review_note": None if aprovar else motivo,
        "reviewed_by": admin_id, "reviewed_at": agora,
    }).eq("id", evento["id"]).execute()
    if aprovar:
        aviso_service.criar([evento["organizer_id"]], "evento_aprovado", "Seu evento foi aprovado e já está no ar",
                            evento["title"], f"/evento/{evento['id']}")
    else:
        aviso_service.criar([evento["organizer_id"]], "evento_recusado", "Seu evento precisa de ajustes",
                            f"{evento['title']}. Motivo: {motivo}", "/meus-eventos")

def marcar_presenca(evento, user_id, vou):
    if vou:
        ja = supabase.table("event_attendance").select("event_id").eq("event_id", evento["id"]).eq("user_id", user_id).execute().data
        if ja:
            return True
        if evento["capacity"] and len(_presencas([evento["id"]])) >= evento["capacity"]:
            return False
        supabase.table("event_attendance").insert({"event_id": evento["id"], "user_id": user_id}).execute()
    else:
        supabase.table("event_attendance").delete().eq("event_id", evento["id"]).eq("user_id", user_id).execute()
    return True
