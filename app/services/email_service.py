import smtplib
from email.message import EmailMessage
from flask import current_app

class EmailIndisponivel(Exception):
    pass

def enviar(para: str, assunto: str, texto: str, html: str):
    config = current_app.config
    if not config.get("SMTP_HOST") or not config.get("SMTP_FROM"):
        raise EmailIndisponivel("O envio de email não está configurado")

    mensagem = EmailMessage()
    mensagem["Subject"] = assunto
    mensagem["From"] = f"Viajá <{config['SMTP_FROM']}>"
    mensagem["To"] = para
    mensagem.set_content(texto)
    mensagem.add_alternative(html, subtype="html")

    with smtplib.SMTP(config["SMTP_HOST"], int(config["SMTP_PORT"]), timeout=20) as servidor:
        if config.get("SMTP_USER"):
            servidor.starttls()
            servidor.login(config["SMTP_USER"], config["SMTP_PASSWORD"])
        servidor.send_message(mensagem)
