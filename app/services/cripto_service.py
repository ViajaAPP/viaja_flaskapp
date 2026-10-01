import base64
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
from flask import current_app

PREFIXO = "v1:"

def _chave():
    texto = current_app.config.get('DADOS_CRYPT_KEY')
    if not texto:
        raise RuntimeError("DADOS_CRYPT_KEY não configurada")
    chave = base64.urlsafe_b64decode(texto)
    if len(chave) != 32:
        raise RuntimeError("DADOS_CRYPT_KEY precisa ter 32 bytes")
    return chave

def gerar_chave():
    return base64.urlsafe_b64encode(AESGCM.generate_key(bit_length=256)).decode()

def cifrar(texto, contexto):
    if texto is None or texto == "" or str(texto).startswith(PREFIXO):
        return texto
    nonce = os.urandom(12)
    cifrado = AESGCM(_chave()).encrypt(nonce, str(texto).encode(), contexto.encode())
    return PREFIXO + base64.urlsafe_b64encode(nonce + cifrado).decode()

def decifrar(texto, contexto):
    if not texto or not str(texto).startswith(PREFIXO):
        return texto
    bruto = base64.urlsafe_b64decode(texto[len(PREFIXO):])
    try:
        return AESGCM(_chave()).decrypt(bruto[:12], bruto[12:], contexto.encode()).decode()
    except InvalidTag:
        current_app.logger.error(f"Não foi possível decifrar um campo de {contexto}")
        return ""
