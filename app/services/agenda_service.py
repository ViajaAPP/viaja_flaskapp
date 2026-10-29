from datetime import datetime, timedelta, timezone
from app.services import supabase_service

DURACAO_PADRAO = timedelta(hours=2)

def _data(texto):
    return datetime.fromisoformat(texto.replace('Z', '+00:00'))

def _janela_da_data(instancia):
    inicio = _data(instancia["start_time"])
    minutos = (instancia.get("tour") or {}).get("estimated_duration_minutes")
    return inicio, inicio + (timedelta(minutes=minutos) if minutos else DURACAO_PADRAO)

def _janela_do_evento(evento):
    inicio = _data(evento["start_time"])
    return inicio, _data(evento["end_time"]) if evento.get("end_time") else inicio + DURACAO_PADRAO

def janela_da_instancia(instancia_id):
    dados = supabase_service.supabase.table("tour_instance").select("id, start_time, tour(title, estimated_duration_minutes)") \
        .eq("id", instancia_id).execute().data or []
    return _janela_da_data(dados[0]) if dados else None

def janela_do_evento(evento_id):
    dados = supabase_service.supabase.table("event").select("id, start_time, end_time").eq("id", evento_id).execute().data or []
    return _janela_do_evento(dados[0]) if dados else None

def compromissos(user_id):
    agora = datetime.now(timezone.utc)
    itens = []
    pedidos = supabase_service.supabase.table("tour_request") \
        .select("status, tour_instance(id, start_time, status, tour(title, estimated_duration_minutes))") \
        .eq("requester_id", user_id).in_("status", ["ACCEPTED", "PENDING"]).execute().data or []
    for pedido in pedidos:
        instancia = pedido.get("tour_instance") or {}
        if not instancia or instancia.get("status") == "CANCELLED":
            continue
        inicio, fim = _janela_da_data(instancia)
        if fim > agora:
            itens.append({"tipo": "passeio", "id": instancia["id"], "titulo": (instancia.get("tour") or {}).get("title"),
                          "inicio": inicio, "fim": fim, "confirmado": pedido["status"] == "ACCEPTED"})
    ids = [p["event_id"] for p in supabase_service.supabase.table("event_attendance").select("event_id").eq("user_id", user_id).execute().data or []]
    if ids:
        eventos = supabase_service.supabase.table("event").select("id, title, start_time, end_time, status").in_("id", ids).eq("status", "PUBLISHED").execute().data or []
        for evento in eventos:
            inicio, fim = _janela_do_evento(evento)
            if fim > agora:
                itens.append({"tipo": "evento", "id": evento["id"], "titulo": evento["title"], "inicio": inicio, "fim": fim, "confirmado": True})
    return itens

def conflitos(user_id, inicio, fim, ignorar=None):
    return [
        {**item, "inicio": item["inicio"].isoformat(), "fim": item["fim"].isoformat()}
        for item in compromissos(user_id)
        if (item["tipo"], item["id"]) != ignorar and item["inicio"] < fim and inicio < item["fim"]
    ]
