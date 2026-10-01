import json
import threading
from flask_sock import Sock, ConnectionClosed
from app.utils.auth import ler_token
from app.services import chat_service

sock = Sock()

ESPERA_DO_LOGIN = 10

chat_subscriptions: dict[str, dict] = {}
subscriptions_lock = threading.Lock()

def subscribe(ws, user_id, chat_ids):
    with subscriptions_lock:
        for chat_id in chat_ids:
            chat_subscriptions.setdefault(str(chat_id), {})[ws] = user_id

def unsubscribe(ws):
    with subscriptions_lock:
        for chat_id in list(chat_subscriptions.keys()):
            chat_subscriptions[chat_id].pop(ws, None)
            if not chat_subscriptions[chat_id]:
                del chat_subscriptions[chat_id]

def publish(chat_id, payload, exceto_user_id=None):
    with subscriptions_lock:
        inscritos = dict(chat_subscriptions.get(str(chat_id), {}))

    mensagem = json.dumps(payload, ensure_ascii=False)
    for ws, user_id in inscritos.items():
        if user_id == exceto_user_id:
            continue
        try:
            ws.send(mensagem)
        except (ConnectionClosed, OSError):
            unsubscribe(ws)

def _login(ws):
    try:
        dados = json.loads(ws.receive(timeout=ESPERA_DO_LOGIN) or "")
    except (TypeError, json.JSONDecodeError):
        return None, []
    if not isinstance(dados, dict) or dados.get("type") != "auth":
        return None, []
    try:
        usuario = ler_token(str(dados.get("token") or ""))
    except Exception:
        return None, []
    pedidos = [int(c) for c in dados.get("chats") or [] if str(c).isdigit()]
    return usuario, chat_service.chats_permitidos(usuario['user_id'], pedidos)

@sock.route('/ws')
def chat_socket(ws):
    usuario, chats = _login(ws)
    if not usuario:
        ws.close(reason=1008, message="Login necessário")
        return
    if not chats:
        ws.close(reason=1008, message="Sem acesso a essas conversas")
        return

    subscribe(ws, usuario['user_id'], chats)
    ws.send(json.dumps({"type": "ready", "chats": chats}))
    for chat_id in chats:
        ws.send(json.dumps({"type": "locations", "chat_id": chat_id, "items": chat_service.localizacoes_recentes(chat_id)}))

    try:
        while True:
            try:
                msg = json.loads(ws.receive() or "")
            except (TypeError, json.JSONDecodeError):
                continue
            if not isinstance(msg, dict):
                continue

            chat_id = msg.get("chat_id")
            if msg.get("type") in ("location", "location_off"):
                if chat_id in chats:
                    payload = chat_service.tratar_localizacao(chat_id, usuario['user_id'], msg)
                    if payload:
                        publish(chat_id, payload, exceto_user_id=usuario['user_id'])
                continue
            if msg.get("type") != "message":
                continue

            texto = str(msg.get("text") or "").strip()
            if chat_id not in chats or not texto:
                continue

            mensagem = chat_service.salvar_mensagem(chat_id, usuario['user_id'], texto)
            if not mensagem:
                continue
            publish(chat_id, {"type": "message", **mensagem}, exceto_user_id=usuario['user_id'])
            ws.send(json.dumps({"type": "sent", "client_id": msg.get("client_id"), **mensagem}, ensure_ascii=False))
    except ConnectionClosed:
        pass
    finally:
        unsubscribe(ws)
