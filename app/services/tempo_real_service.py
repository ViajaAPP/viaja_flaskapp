import json
import threading

conexoes: dict[int, set] = {}
conexoes_lock = threading.Lock()

def entrar(user_id, ws):
    with conexoes_lock:
        conexoes.setdefault(user_id, set()).add(ws)

def sair(user_id, ws):
    with conexoes_lock:
        abertas = conexoes.get(user_id)
        if abertas:
            abertas.discard(ws)
            if not abertas:
                del conexoes[user_id]

def enviar(user_ids, payload):
    mensagem = json.dumps(payload, ensure_ascii=False)
    for user_id in user_ids:
        with conexoes_lock:
            abertas = list(conexoes.get(user_id, ()))
        for ws in abertas:
            try:
                ws.send(mensagem)
            except Exception:
                sair(user_id, ws)
