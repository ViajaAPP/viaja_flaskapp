from datetime import datetime, timedelta, timezone
from app.services.supabase_service import supabase
from app.services import aviso_service, review_service

PRAZO_DE_RESPOSTA = timedelta(hours=24)

def _data(texto):
    return datetime.fromisoformat(texto.replace('Z', '+00:00'))

def expirar_pedidos():
    limite = (datetime.now(timezone.utc) - PRAZO_DE_RESPOSTA).isoformat()
    vencidos = supabase.table("tour_request").select("id, requester_id, tour_instance(start_time, tour(id, title))") \
        .eq("status", "PENDING").lt("created_at", limite).execute().data or []
    if not vencidos:
        return
    supabase.table("tour_request").update({"status": "EXPIRED", "last_updated": datetime.now(timezone.utc).isoformat()}) \
        .in_("id", [p["id"] for p in vencidos]).execute()
    for pedido in vencidos:
        instancia = pedido.get("tour_instance") or {}
        tour = instancia.get("tour") or {}
        aviso_service.criar([pedido["requester_id"]], "pedido_expirado", "Seu pedido expirou sem resposta",
                            f"{tour.get('title', 'Passeio')}. O guia não respondeu em 24 horas. Tente outra data ou outro passeio.",
                            f"/passeio/{tour.get('id')}" if tour.get('id') else None)

def _pessoas(user_ids):
    if not user_ids:
        return {}
    dados = supabase.table("user").select("user_id, first_name, last_name, photo").in_("user_id", list(user_ids)).execute().data or []
    return {u["user_id"]: u for u in dados}

def _datas_do_guia(guia_id):
    tours = supabase.table("tour").select("id, title, photo, price, min_participants, instant_booking").eq("created_by_id", guia_id).execute().data or []
    if not tours:
        return {}, []
    por_id = {t["id"]: t for t in tours}
    instancias = supabase.table("tour_instance").select("id, tour_id, start_time, max_capacity, status, registration") \
        .in_("tour_id", list(por_id)).execute().data or []
    return por_id, instancias

def pedidos_do_guia(guia_id):
    expirar_pedidos()
    tours, instancias = _datas_do_guia(guia_id)
    if not instancias:
        return {"esperando": [], "respondidos": []}
    instancia_por_id = {i["id"]: i for i in instancias}
    pedidos = supabase.table("tour_request").select("id, tour_instance_id, requester_id, status, message, created_at, last_updated") \
        .in_("tour_instance_id", list(instancia_por_id)).order("created_at", desc=True).limit(200).execute().data or []
    pessoas = _pessoas({p["requester_id"] for p in pedidos})
    agora = datetime.now(timezone.utc)
    esperando, respondidos = [], []
    for pedido in pedidos:
        instancia = instancia_por_id[pedido["tour_instance_id"]]
        tour = tours[instancia["tour_id"]]
        pessoa = pessoas.get(pedido["requester_id"]) or {}
        item = {
            **pedido,
            "tour_id": tour["id"], "tour_title": tour["title"], "tour_photo": tour["photo"],
            "start_time": instancia["start_time"], "max_capacity": instancia["max_capacity"],
            "requester": pessoa,
            "expires_at": (_data(pedido["created_at"]) + PRAZO_DE_RESPOSTA).isoformat(),
        }
        if pedido["status"] == "PENDING":
            esperando.append(item)
        elif _data(instancia["start_time"]) > agora - timedelta(days=7):
            respondidos.append(item)
    esperando.sort(key=lambda p: p["expires_at"])
    return {"esperando": esperando, "respondidos": respondidos[:30]}

def agenda_do_guia(guia_id):
    tours, instancias = _datas_do_guia(guia_id)
    agora = datetime.now(timezone.utc)
    futuras = [i for i in instancias if _data(i["start_time"]) > agora - timedelta(hours=6) and i["status"] != "CANCELLED"]
    if not futuras:
        return []
    ids = [i["id"] for i in futuras]
    pedidos = supabase.table("tour_request").select("tour_instance_id, status").in_("tour_instance_id", ids).execute().data or []
    chats = supabase.table("chat").select("id, tour_instance_id").in_("tour_instance_id", ids).execute().data or []
    chat_por_instancia = {c["tour_instance_id"]: c["id"] for c in chats}
    agenda = []
    for instancia in sorted(futuras, key=lambda i: i["start_time"]):
        tour = tours[instancia["tour_id"]]
        confirmados = sum(1 for p in pedidos if p["tour_instance_id"] == instancia["id"] and p["status"] == "ACCEPTED")
        esperando = sum(1 for p in pedidos if p["tour_instance_id"] == instancia["id"] and p["status"] == "PENDING")
        agenda.append({
            **instancia,
            "tour_title": tour["title"], "tour_photo": tour["photo"], "price": tour["price"],
            "min_participants": tour["min_participants"],
            "confirmed": confirmados, "pending": esperando,
            "chat_id": chat_por_instancia.get(instancia["id"]),
        })
    return agenda

def viagens_do_viajante(user_id):
    expirar_pedidos()
    pedidos = supabase.table("tour_request") \
        .select("id, status, message, created_at, tour_instance(id, start_time, status, max_capacity, tour(id, title, photo, price, meeting_point, created_by_id, min_participants))") \
        .eq("requester_id", user_id).order("created_at", desc=True).execute().data or []
    guias = _pessoas({(p.get("tour_instance") or {}).get("tour", {}).get("created_by_id") for p in pedidos} - {None})
    instancias = [p["tour_instance"]["id"] for p in pedidos if p.get("tour_instance")]
    chats = supabase.table("chat").select("id, tour_instance_id").in_("tour_instance_id", instancias).execute().data if instancias else []
    chat_por_instancia = {c["tour_instance_id"]: c["id"] for c in chats or []}
    avaliadas = {r["tour_instance_id"] for r in supabase.table("tour_review").select("tour_instance_id").eq("user_id", user_id).execute().data or []}
    agora = datetime.now(timezone.utc)
    grupos = {"proximas": [], "esperando": [], "passadas": [], "encerradas": []}
    for pedido in pedidos:
        instancia = pedido.get("tour_instance") or {}
        tour = instancia.get("tour") or {}
        if not instancia or not tour:
            continue
        inicio = _data(instancia["start_time"])
        item = {
            "id": pedido["id"], "status": pedido["status"], "created_at": pedido["created_at"],
            "instance_id": instancia["id"], "start_time": instancia["start_time"], "instance_status": instancia["status"],
            "tour_id": tour["id"], "tour_title": tour["title"], "tour_photo": tour["photo"], "price": tour["price"],
            "meeting_point": tour["meeting_point"], "guide": guias.get(tour["created_by_id"]),
            "chat_id": chat_por_instancia.get(instancia["id"]),
            "can_review": pedido["status"] == "ACCEPTED" and inicio < agora and instancia["status"] != "CANCELLED" and instancia["id"] not in avaliadas,
            "expires_at": (_data(pedido["created_at"]) + PRAZO_DE_RESPOSTA).isoformat(),
        }
        if instancia["status"] == "CANCELLED" or pedido["status"] in ("DENIED", "EXPIRED", "CANCELLED"):
            grupos["encerradas"].append(item)
        elif pedido["status"] == "PENDING":
            grupos["esperando"].append(item)
        elif inicio >= agora:
            grupos["proximas"].append(item)
        else:
            grupos["passadas"].append(item)
    grupos["proximas"].sort(key=lambda i: i["start_time"])
    return grupos

def contagem_do_guia(guia_id):
    tours, instancias = _datas_do_guia(guia_id)
    if not instancias:
        return 0
    resposta = supabase.table("tour_request").select("id", count="exact").eq("status", "PENDING") \
        .in_("tour_instance_id", [i["id"] for i in instancias]).execute()
    return resposta.count or 0

def arquivados_do_guia(guia_id):
    expirar_pedidos()
    tours, instancias = _datas_do_guia(guia_id)
    if not instancias:
        return {"pedidos": [], "datas": []}
    agora = datetime.now(timezone.utc)
    limite = agora - timedelta(days=180)
    instancia_por_id = {i["id"]: i for i in instancias}
    pedidos = supabase.table("tour_request").select("id, tour_instance_id, requester_id, status, message, created_at, last_updated")         .in_("tour_instance_id", list(instancia_por_id)).in_("status", ["DENIED", "EXPIRED", "CANCELLED"])         .order("created_at", desc=True).limit(100).execute().data or []
    pessoas = _pessoas({p["requester_id"] for p in pedidos})
    itens_pedidos = []
    for pedido in pedidos:
        instancia = instancia_por_id[pedido["tour_instance_id"]]
        tour = tours[instancia["tour_id"]]
        itens_pedidos.append({
            **pedido, "tour_id": tour["id"], "tour_title": tour["title"], "tour_photo": tour["photo"],
            "start_time": instancia["start_time"], "max_capacity": instancia["max_capacity"],
            "requester": pessoas.get(pedido["requester_id"]) or {},
        })
    passadas = [
        i for i in instancias
        if limite < _data(i["start_time"]) and (_data(i["start_time"]) < agora - timedelta(hours=6) or i["status"] == "CANCELLED")
    ]
    confirmados = {}
    if passadas:
        aceitos = supabase.table("tour_request").select("tour_instance_id").eq("status", "ACCEPTED")             .in_("tour_instance_id", [i["id"] for i in passadas]).execute().data or []
        for pedido in aceitos:
            confirmados[pedido["tour_instance_id"]] = confirmados.get(pedido["tour_instance_id"], 0) + 1
    datas = [{
        **i, "tour_title": tours[i["tour_id"]]["title"], "tour_photo": tours[i["tour_id"]]["photo"],
        "confirmed": confirmados.get(i["id"], 0),
    } for i in sorted(passadas, key=lambda i: i["start_time"], reverse=True)]
    return {"pedidos": itens_pedidos, "datas": datas}
