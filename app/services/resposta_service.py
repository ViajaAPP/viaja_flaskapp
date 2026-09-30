from datetime import datetime, timedelta, timezone
from statistics import median
from app.services.supabase_service import supabase

JANELA_DIAS = 90
MINIMO_DE_RESPOSTAS = 3

def _data(texto):
    return datetime.fromisoformat(texto.replace('Z', '+00:00'))

def _horas_dos_pedidos(instancias, desde):
    if not instancias:
        return []
    pedidos = supabase.table("tour_request").select("created_at, last_updated, status") \
        .in_("tour_instance_id", list(instancias)).neq("status", "PENDING").gte("created_at", desde).execute().data or []
    return [
        (_data(p["last_updated"]) - _data(p["created_at"])).total_seconds() / 3600
        for p in pedidos if p.get("last_updated")
    ]

def _horas_do_chat(guia_id, instancias, desde):
    if not instancias:
        return []
    chats = supabase.table("chat").select("id").in_("tour_instance_id", list(instancias)).execute().data or []
    if not chats:
        return []
    mensagens = supabase.table("chat_message").select("chat_id, user_id, created_at") \
        .in_("chat_id", [c["id"] for c in chats]).gte("created_at", desde).order("created_at").limit(2000).execute().data or []
    horas, esperando = [], {}
    for mensagem in mensagens:
        if mensagem["user_id"] == guia_id:
            inicio = esperando.pop(mensagem["chat_id"], None)
            if inicio:
                horas.append((_data(mensagem["created_at"]) - inicio).total_seconds() / 3600)
        else:
            esperando.setdefault(mensagem["chat_id"], _data(mensagem["created_at"]))
    return horas

def _rotulo(horas):
    if horas < 1:
        return "em menos de 1 hora"
    if horas < 3:
        return "em até 3 horas"
    if horas < 12:
        return "em até 12 horas"
    if horas < 24:
        return "em até 1 dia"
    return "em alguns dias"

def tempo_de_resposta(guia_id):
    desde = (datetime.now(timezone.utc) - timedelta(days=JANELA_DIAS)).isoformat()
    tours = supabase.table("tour").select("id").eq("created_by_id", guia_id).execute().data or []
    if not tours:
        return None
    instancias = {i["id"] for i in supabase.table("tour_instance").select("id").in_("tour_id", [t["id"] for t in tours]).execute().data or []}
    horas = _horas_dos_pedidos(instancias, desde) + _horas_do_chat(guia_id, instancias, desde)
    if len(horas) < MINIMO_DE_RESPOSTAS:
        return None
    mediana = median(horas)
    return {"hours": round(mediana, 1), "label": _rotulo(mediana), "samples": len(horas)}
