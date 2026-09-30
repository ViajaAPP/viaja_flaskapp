import hashlib
import secrets
from datetime import datetime, timedelta, timezone
import bcrypt
from flask import current_app
from app.services.supabase_service import supabase
from app.services import email_service

VALIDADE = timedelta(minutes=30)

def _hash(codigo: str) -> str:
    return hashlib.sha256(codigo.encode()).hexdigest()

def pedir_troca(email: str):
    resposta = supabase.table("user").select("user_id, first_name, email").eq("email", email).execute()
    if not resposta.data:
        return
    usuario = resposta.data[0]

    agora = datetime.now(timezone.utc)
    supabase.table("password_reset").update({"used_at": agora.isoformat()}) \
        .eq("user_id", usuario["user_id"]).is_("used_at", "null").execute()

    codigo = secrets.token_urlsafe(32)
    supabase.table("password_reset").insert({
        "user_id": usuario["user_id"],
        "token_hash": _hash(codigo),
        "expires_at": (agora + VALIDADE).isoformat(),
    }).execute()

    link = f"{current_app.config['APP_URL'].rstrip('/')}/redefinir-senha?codigo={codigo}"
    nome = usuario.get("first_name") or ""
    texto = (
        f"Oi, {nome}!\n\n"
        "Recebemos um pedido para trocar a senha da sua conta no Viajá.\n"
        f"Para escolher uma senha nova, abra este link nos próximos 30 minutos:\n{link}\n\n"
        "Se não foi você, é só ignorar este email. Sua senha continua a mesma."
    )
    html = (
        f"<p>Oi, {nome}!</p>"
        "<p>Recebemos um pedido para trocar a senha da sua conta no Viajá.</p>"
        f"<p><a href=\"{link}\">Escolher uma senha nova</a></p>"
        "<p>O link vale por 30 minutos. Se não foi você, é só ignorar este email. Sua senha continua a mesma.</p>"
    )
    email_service.enviar(usuario["email"], "Troca de senha no Viajá", texto, html)

def trocar_senha(codigo: str, senha: str) -> bool:
    resposta = supabase.table("password_reset").select("id, user_id, expires_at, used_at") \
        .eq("token_hash", _hash(codigo)).execute()
    if not resposta.data:
        return False
    pedido = resposta.data[0]
    agora = datetime.now(timezone.utc)
    if pedido["used_at"] or datetime.fromisoformat(pedido["expires_at"]) <= agora:
        return False

    senha_hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
    supabase.table("user").update({"password": senha_hash}).eq("user_id", pedido["user_id"]).execute()
    supabase.table("password_reset").update({"used_at": agora.isoformat()}).eq("id", pedido["id"]).execute()
    return True
