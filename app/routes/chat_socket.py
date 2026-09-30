import json
import threading
from flask import request
from flask_sock import Sock, ConnectionClosed

sock = Sock()

chat_subscriptions: dict[str, set] = {}
subscriptions_lock = threading.Lock()

def subscribe(ws, chat_ids: list[str]):
    with subscriptions_lock:
        for chat_id in chat_ids:
            chat_subscriptions.setdefault(chat_id, set()).add(ws)

def unsubscribe(ws):
    with subscriptions_lock:
        for chat_id in list(chat_subscriptions.keys()):
            chat_subscriptions[chat_id].discard(ws)
            if not chat_subscriptions[chat_id]:
                del chat_subscriptions[chat_id]

def publish(chat_id: str, payload: dict, sender_ws):
    with subscriptions_lock:
        subscribers = set(chat_subscriptions.get(chat_id, set()))

    message = json.dumps(payload, ensure_ascii=False)
    for ws in subscribers:
        if ws is sender_ws:
            continue
        try:
            ws.send(message)
        except (ConnectionClosed, OSError):
            unsubscribe(ws)

@sock.route('/ws')
def chat_socket(ws):
    user_id = request.args.get("user_id")
    if not user_id:
        ws.close(reason=1008, message="Missing user_id")
        return

    chat_ids = [c.strip() for c in request.args.get("chats", "").split(",") if c.strip()]
    subscribe(ws, chat_ids)

    try:
        while True:
            data = ws.receive()
            try:
                msg = json.loads(data)
            except (TypeError, json.JSONDecodeError):
                continue

            chat_id = msg.get("chat_id")
            text = msg.get("text")
            if chat_id is None or not text:
                continue

            publish(str(chat_id), {
                "type": "message",
                "chat_id": str(chat_id),
                "user_id": user_id,
                "text": text,
            }, sender_ws=ws)
    except ConnectionClosed:
        pass
    finally:
        unsubscribe(ws)
