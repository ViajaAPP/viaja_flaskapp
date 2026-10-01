from app.services.supabase_service import supabase
from app.services import cripto_service

CONTEXTO = "chat_message"

def instancias_do_usuario(user_id):
    tours = supabase.table("tour").select("id").eq("created_by_id", user_id).execute().data or []
    ids = set()
    if tours:
        instancias = supabase.table("tour_instance").select("id").in_("tour_id", [t['id'] for t in tours]).execute().data or []
        ids.update(i['id'] for i in instancias)
    pedidos = (
        supabase.table("tour_request")
        .select("tour_instance_id")
        .eq("requester_id", user_id)
        .eq("status", "ACCEPTED")
        .execute()
        .data or []
    )
    ids.update(p['tour_instance_id'] for p in pedidos)
    return sorted(ids)

def buscar_chat(chat_id):
    dados = supabase.table("chat").select("id, tour_instance_id").eq("id", chat_id).execute().data
    return dados[0] if dados else None

def participa(user_id, chat):
    instancia = supabase.table("tour_instance").select("tour_id").eq("id", chat['tour_instance_id']).execute().data
    if not instancia:
        return False
    tour = supabase.table("tour").select("created_by_id").eq("id", instancia[0]['tour_id']).execute().data
    if tour and tour[0]['created_by_id'] == user_id:
        return True
    aceito = (
        supabase.table("tour_request")
        .select("id")
        .eq("tour_instance_id", chat['tour_instance_id'])
        .eq("requester_id", user_id)
        .eq("status", "ACCEPTED")
        .limit(1)
        .execute()
        .data
    )
    return bool(aceito)

def chats_permitidos(user_id, chat_ids):
    permitidos = []
    for chat_id in chat_ids:
        chat = buscar_chat(chat_id)
        if chat and participa(user_id, chat):
            permitidos.append(chat['id'])
    return permitidos

def _abrir(mensagem):
    return {**mensagem, "text": cripto_service.decifrar(mensagem.get("text"), CONTEXTO)}

def ultimas_mensagens(chat_id, limite=20, inicio=0):
    dados = (
        supabase.table("chat_message")
        .select("*")
        .eq("chat_id", chat_id)
        .order("created_at", desc=True)
        .range(inicio, inicio + limite - 1)
        .execute()
        .data or []
    )
    return [_abrir(m) for m in dados]

def salvar_mensagem(chat_id, user_id, texto):
    dados = supabase.table("chat_message").insert({
        "user_id": user_id,
        "chat_id": chat_id,
        "text": cripto_service.cifrar(texto, CONTEXTO),
    }).execute().data
    return _abrir(dados[0]) if dados else None
