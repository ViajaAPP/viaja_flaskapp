import socket
import threading
import hashlib
import base64
import json
import struct
from pyngrok import ngrok
from dotenv import load_dotenv
from typing import Optional, Union
import os
from app.utils.auth import ler_token
from app.services import chat_service

load_dotenv()

NGROK_AUTH_TOKEN = os.getenv('NGROK_WS_TOKEN')
if NGROK_AUTH_TOKEN:
    ngrok.set_auth_token(NGROK_AUTH_TOKEN)

ESPERA_DO_LOGIN = 10

chat_subscriptions: dict[str, set[socket.socket]] = {}
client_meta: dict[socket.socket, dict] = {}
subscriptions_lock = threading.Lock()

def parse_handshake(data: bytes) -> dict:
    """
    Extrai headers HTTP do handshake e os query params da URL.
    O cliente conecta em ws://host/ws e manda o login na primeira mensagem.
    """
    lines = data.decode("utf-8").split("\r\n")
    headers = {}
    request_line = lines[0]

    for line in lines[1:]:
        if ": " in line:
            key, val = line.split(": ", 1)
            headers[key.lower()] = val

    # Extrai query string da URL
    path = request_line.split(" ")[1]
    query_params = {}
    if "?" in path:
        qs = path.split("?", 1)[1]
        for param in qs.split("&"):
            if "=" in param:
                k, v = param.split("=", 1)
                query_params[k] = v

    return {"headers": headers, "params": query_params}

def perform_handshake(conn: socket.socket, data: bytes) -> Optional[dict]:
    """
    Completa o handshake WebSocket (RFC 6455) e retorna os metadados do cliente.
    Retorna None se o handshake falhar.
    """
    parsed = parse_handshake(data)
    headers = parsed["headers"]
    params = parsed["params"]

    if "sec-websocket-key" not in headers:
        conn.send(b"HTTP/1.1 400 Bad Request\r\n\r\n")
        return None

    magic = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    key = headers["sec-websocket-key"] + magic
    accept = base64.b64encode(hashlib.sha1(key.encode()).digest()).decode()

    response = (
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Accept: {accept}\r\n"
        "\r\n"
    )
    conn.send(response.encode())

    return {"params": params}

def decode_frame(data: bytes) -> Optional[dict]:
    """Decodifica um frame WebSocket recebido do cliente. Retorna None se o frame for inválido."""
    if len(data) < 2:
        return None

    fin = (data[0] >> 7) & 1
    opcode = data[0] & 0x0F
    masked = (data[1] >> 7) & 1
    payload_len = data[1] & 0x7F

    offset = 2
    if payload_len == 126:
        payload_len = struct.unpack(">H", data[offset:offset+2])[0]
        offset += 2
    elif payload_len == 127:
        payload_len = struct.unpack(">Q", data[offset:offset+8])[0]
        offset += 8

    mask_key = b""
    if masked:
        mask_key = data[offset:offset+4]
        offset += 4

    payload = bytearray(data[offset:offset+payload_len])
    if masked:
        payload = bytearray(b ^ mask_key[i % 4] for i, b in enumerate(payload))

    return {"opcode": opcode, "payload": bytes(payload), "fin": fin}


def encode_frame(message: Union[str, bytes]) -> bytes:
    """Encoda um frame WebSocket texto."""
    if isinstance(message, str):
        message = message.encode("utf-8")

    length = len(message)
    if length <= 125:
        header = bytes([0x81, length])
    elif length <= 65535:
        header = bytes([0x81, 126]) + struct.pack(">H", length)
    else:
        header = bytes([0x81, 127]) + struct.pack(">Q", length)

    return header + message

def encode_close(code: int, reason: str) -> bytes:
    """Encoda um frame WebSocket de fechamento com o código e o motivo."""
    payload = struct.pack(">H", code) + reason.encode("utf-8")
    return bytes([0x88, len(payload)]) + payload

def enviar(conn: socket.socket, payload: dict):
    conn.sendall(encode_frame(json.dumps(payload, ensure_ascii=False)))

def ler_texto(conn: socket.socket) -> Optional[dict]:
    """Lê um frame de texto e devolve o JSON, ou None se a conexão fechou."""
    data = conn.recv(4096)
    if not data:
        return None
    frame = decode_frame(data)
    if frame is None or frame["opcode"] == 8:
        return None
    if frame["opcode"] != 1:
        return {}
    try:
        msg = json.loads(frame["payload"].decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return msg if isinstance(msg, dict) else {}

def login(conn: socket.socket, app):
    """Espera o login na primeira mensagem e devolve o usuário e os chats dos passeios dele."""
    conn.settimeout(ESPERA_DO_LOGIN)
    try:
        msg = ler_texto(conn)
    except socket.timeout:
        return None, []
    finally:
        conn.settimeout(None)
    if not msg or msg.get("type") != "auth":
        return None, []
    with app.app_context():
        try:
            usuario = ler_token(str(msg.get("token") or ""))
        except Exception:
            return None, []
        pedidos = [int(c) for c in msg.get("chats") or [] if str(c).isdigit()]
        return usuario, [str(c) for c in chat_service.chats_permitidos(usuario["user_id"], pedidos)]

def subscribe(conn: socket.socket, chat_ids: list[str]):
    """
    Registra a conexão nos chats desejados.
    Usa lock para garantir exclusão mútua (thread-safety).
    """
    with subscriptions_lock:
        for chat_id in chat_ids:
            if chat_id not in chat_subscriptions:
                chat_subscriptions[chat_id] = set()
            chat_subscriptions[chat_id].add(conn)
    print(f"[subscriptions] {conn.getpeername()} -> chats: {chat_ids}")


def unsubscribe(conn: socket.socket):
    """Remove a conexão de todos os chats ao desconectar."""
    with subscriptions_lock:
        for chat_id in list(chat_subscriptions.keys()):
            chat_subscriptions[chat_id].discard(conn)
            if not chat_subscriptions[chat_id]:
                del chat_subscriptions[chat_id]
        client_meta.pop(conn, None)
    print(f"[subscriptions] conexão removida: {conn.getpeername()}")

def publish(chat_id: str, payload: dict, sender_conn: socket.socket):
    """
    Envia a mensagem para todos os subscribers do chat,
    exceto o remetente (comportamento típico de chat).
    """
    chat_id = str(chat_id)

    with subscriptions_lock:
        subscribers = set(chat_subscriptions.get(chat_id, set()))

    frame = encode_frame(json.dumps(payload, ensure_ascii=False))

    dead_conns = []
    for conn in subscribers:
        if conn is sender_conn:
            continue  # não envia de volta ao remetente
        try:
            conn.sendall(frame)
        except (BrokenPipeError, OSError):
            dead_conns.append(conn)

    # Limpeza lazy de conexões mortas
    for conn in dead_conns:
        unsubscribe(conn)

def handle_client(conn: socket.socket, addr, app):
    print(f"[+] Nova conexão: {addr}")
    try:
        # 1. Receber handshake HTTP
        raw = conn.recv(4096)
        if not raw:
            return

        meta = perform_handshake(conn, raw)
        if not meta:
            return

        # 2. Login na primeira mensagem, só com os chats dos passeios dessa conta
        usuario, chat_ids = login(conn, app)
        if not usuario or not chat_ids:
            conn.sendall(encode_close(1008, "Login necessário"))
            return

        user_id = usuario["user_id"]
        with subscriptions_lock:
            client_meta[conn] = {"user_id": user_id, "chat_ids": chat_ids}
        subscribe(conn, chat_ids)
        enviar(conn, {"type": "ready", "chats": [int(c) for c in chat_ids]})

        # 3. Loop de leitura de mensagens
        while True:
            msg = ler_texto(conn)
            if msg is None:
                break
            if msg.get("type") != "message":
                continue

            chat_id = str(msg.get("chat_id"))
            text = str(msg.get("text") or "").strip()
            if chat_id not in chat_ids or not text:
                continue

            with app.app_context():
                mensagem = chat_service.salvar_mensagem(int(chat_id), user_id, text)
            if not mensagem:
                continue

            publish(chat_id, {"type": "message", **mensagem}, sender_conn=conn)
            enviar(conn, {"type": "sent", "client_id": msg.get("client_id"), **mensagem})

    except Exception as e:
        print(f"[erro] {addr}: {type(e).__name__}")
    finally:
        unsubscribe(conn)
        conn.close()
        print(f"[-] Desconectado: {addr}")

def start_server_socket(app, host="0.0.0.0", port=8765):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(50)
    print(f"[server] Servidor rodando localmente em {host}:{port}")

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr, app), daemon=True)
        thread.start()

# public_url = ngrok.connect(8765, "tcp")
# print(f"[server] Túnel ngrok aberto: {public_url}")

# server_thread = threading.Thread(target=start_server_socket, daemon=True)
# server_thread.start()
