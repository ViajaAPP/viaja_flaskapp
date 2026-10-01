import threading
import time
from datetime import datetime, timedelta, timezone
from app.services import supabase_service
from app.services import cripto_service

CONTEXTO = "chat_message"
ABRE_ANTES = timedelta(hours=2)
DURACAO_PADRAO_DO_EVENTO = timedelta(hours=4)
VALIDADE_DA_LOCALIZACAO = 10 * 60
VALIDADE_DA_JANELA = 60

_localizacoes: dict[str, dict[int, dict]] = {}
_janelas: dict[str, tuple[float, bool]] = {}
_trava = threading.Lock()

def instancias_do_usuario(user_id):
    tours = supabase_service.supabase.table("tour").select("id").eq("created_by_id", user_id).execute().data or []
    ids = set()
    if tours:
        instancias = supabase_service.supabase.table("tour_instance").select("id").in_("tour_id", [t['id'] for t in tours]).execute().data or []
        ids.update(i['id'] for i in instancias)
    pedidos = (
        supabase_service.supabase.table("tour_request")
        .select("tour_instance_id")
        .eq("requester_id", user_id)
        .eq("status", "ACCEPTED")
        .execute()
        .data or []
    )
    ids.update(p['tour_instance_id'] for p in pedidos)
    return sorted(ids)

def buscar_chat(chat_id):
    dados = supabase_service.supabase.table("chat").select("id, tour_instance_id, event_id").eq("id", chat_id).execute().data
    return dados[0] if dados else None

def chat_do_evento(event_id):
    db = supabase_service.supabase
    dados = db.table("chat").select("id").eq("event_id", event_id).execute().data
    if dados:
        return dados[0]["id"]
    try:
        return db.table("chat").insert({"event_id": event_id}).execute().data[0]["id"]
    except Exception:
        return db.table("chat").select("id").eq("event_id", event_id).execute().data[0]["id"]

def _participa_do_evento(user_id, event_id):
    db = supabase_service.supabase
    evento = db.table("event").select("organizer_id").eq("id", event_id).execute().data
    if evento and evento[0]["organizer_id"] == user_id:
        return True
    return bool(db.table("event_attendance").select("user_id").eq("event_id", event_id).eq("user_id", user_id).limit(1).execute().data)

def participa(user_id, chat):
    if chat.get('event_id'):
        return _participa_do_evento(user_id, chat['event_id'])
    instancia = supabase_service.supabase.table("tour_instance").select("tour_id").eq("id", chat['tour_instance_id']).execute().data
    if not instancia:
        return False
    tour = supabase_service.supabase.table("tour").select("created_by_id").eq("id", instancia[0]['tour_id']).execute().data
    if tour and tour[0]['created_by_id'] == user_id:
        return True
    aceito = (
        supabase_service.supabase.table("tour_request")
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
        supabase_service.supabase.table("chat_message")
        .select("*")
        .eq("chat_id", chat_id)
        .order("created_at", desc=True)
        .range(inicio, inicio + limite - 1)
        .execute()
        .data or []
    )
    return [_abrir(m) for m in dados]

def salvar_mensagem(chat_id, user_id, texto):
    dados = supabase_service.supabase.table("chat_message").insert({
        "user_id": user_id,
        "chat_id": chat_id,
        "text": cripto_service.cifrar(texto, CONTEXTO),
    }).execute().data
    return _abrir(dados[0]) if dados else None

def _data(texto):
    return datetime.fromisoformat(texto.replace("Z", "+00:00"))

def mapa_do_chat(chat):
    db = supabase_service.supabase
    if chat.get('event_id'):
        dados = db.table("event").select("start_time, end_time, place_name, address(lat, lon, street, number, city)").eq("id", chat['event_id']).execute().data
        if not dados:
            return None
        evento = dados[0]
        inicio = _data(evento["start_time"])
        fim = _data(evento["end_time"]) if evento.get("end_time") else inicio + DURACAO_PADRAO_DO_EVENTO
        endereco = evento.get("address") or {}
        ponto = evento.get("place_name")
    else:
        dados = (
            db.table("tour_instance")
            .select("start_time, tour(meeting_point, estimated_duration_minutes, address(lat, lon, street, number, city))")
            .eq("id", chat['tour_instance_id'])
            .execute()
            .data
        )
        if not dados:
            return None
        instancia = dados[0]
        tour = instancia.get("tour") or {}
        inicio = _data(instancia["start_time"])
        fim = inicio + timedelta(minutes=tour.get("estimated_duration_minutes") or 120)
        endereco = tour.get("address") or {}
        ponto = tour.get("meeting_point")
    abre = inicio - ABRE_ANTES
    agora = datetime.now(timezone.utc)
    return {
        "opens_at": abre.isoformat(),
        "closes_at": fim.isoformat(),
        "open": abre <= agora <= fim,
        "meeting_point": ponto,
        "lat": endereco.get("lat"),
        "lon": endereco.get("lon"),
    }

def mapa_aberto(chat_id):
    chave = str(chat_id)
    agora = time.time()
    with _trava:
        guardado = _janelas.get(chave)
    if guardado and guardado[0] > agora:
        return guardado[1]
    chat = buscar_chat(chat_id)
    mapa = mapa_do_chat(chat) if chat else None
    aberto = bool(mapa and mapa["open"])
    with _trava:
        _janelas[chave] = (agora + VALIDADE_DA_JANELA, aberto)
    return aberto

def _coordenada(valor, limite):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return round(numero, 5) if -limite <= numero <= limite else None

def registrar_localizacao(chat_id, user_id, lat, lon):
    lat, lon = _coordenada(lat, 90), _coordenada(lon, 180)
    if lat is None or lon is None:
        return None
    payload = {"type": "location", "chat_id": int(chat_id), "user_id": user_id, "lat": lat, "lon": lon, "at": int(time.time())}
    with _trava:
        _localizacoes.setdefault(str(chat_id), {})[user_id] = payload
    return payload

def remover_localizacao(chat_id, user_id):
    with _trava:
        (_localizacoes.get(str(chat_id)) or {}).pop(user_id, None)
    return {"type": "location_off", "chat_id": int(chat_id), "user_id": user_id}

def localizacoes_recentes(chat_id):
    limite = time.time() - VALIDADE_DA_LOCALIZACAO
    with _trava:
        do_chat = _localizacoes.get(str(chat_id)) or {}
        for user_id in [u for u, p in do_chat.items() if p["at"] < limite]:
            do_chat.pop(user_id, None)
        return list(do_chat.values())

def tratar_localizacao(chat_id, user_id, msg):
    if msg.get("type") == "location_off":
        return remover_localizacao(chat_id, user_id)
    if not mapa_aberto(chat_id):
        return None
    return registrar_localizacao(chat_id, user_id, msg.get("lat"), msg.get("lon"))

def _pessoas(user_ids):
    if not user_ids:
        return []
    return (
        supabase_service.supabase.table("user")
        .select("user_id, first_name, last_name, photo")
        .in_("user_id", list(user_ids))
        .execute()
        .data or []
    )

def nome_e_membros(chat):
    db = supabase_service.supabase
    if chat.get('event_id'):
        evento = db.table("event").select("title, organizer_id").eq("id", chat['event_id']).execute().data
        if not evento:
            return "", []
        vao = db.table("event_attendance").select("user_id").eq("event_id", chat['event_id']).execute().data or []
        return evento[0]["title"], _pessoas({evento[0]["organizer_id"], *(v["user_id"] for v in vao)})
    titulo = db.rpc('get_tour_by_chat', {"chat_id": chat['id']}).execute().data or []
    membros = db.rpc('get_tour_members', {"tour_instance_id": chat['tour_instance_id']}).execute().data or []
    return (
        titulo[0]['tour_title'] if titulo else "",
        [{"user_id": m['user_id'], "first_name": m['first_name'], "last_name": m['last_name'], "photo": m['photo']} for m in membros],
    )

def grupos_de_evento(user_id):
    db = supabase_service.supabase
    desde = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    vou = {v["event_id"] for v in db.table("event_attendance").select("event_id").eq("user_id", user_id).execute().data or []}
    organizo = {e["id"] for e in db.table("event").select("id").eq("organizer_id", user_id).execute().data or []}
    ids = vou | organizo
    if not ids:
        return []
    eventos = (
        db.table("event")
        .select("id, title, photo, start_time")
        .in_("id", list(ids))
        .eq("status", "PUBLISHED")
        .gte("start_time", desde)
        .order("start_time")
        .execute()
        .data or []
    )
    grupos = []
    for evento in eventos:
        chat = {"id": chat_do_evento(evento["id"]), "event_id": evento["id"]}
        _, membros = nome_e_membros(chat)
        grupos.append({**evento, "chat_id": chat["id"], "members": membros})
    return grupos
