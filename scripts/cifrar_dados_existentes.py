import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.services import supabase_service
from app.services import cripto_service

CAMPOS = [
    ("chat_message", "id", "text", "chat_message"),
    ("user", "user_id", "phone", "user.phone"),
]

def cifrar_tabela(tabela, chave, campo, contexto):
    linhas = supabase_service.supabase.table(tabela).select(f"{chave}, {campo}").execute().data or []
    pendentes = [l for l in linhas if l[campo] and not str(l[campo]).startswith(cripto_service.PREFIXO)]
    for linha in pendentes:
        supabase_service.supabase.table(tabela).update({campo: cripto_service.cifrar(linha[campo], contexto)}).eq(chave, linha[chave]).execute()
    print(f"{tabela}.{campo}: {len(pendentes)} de {len(linhas)} cifrados agora")

if __name__ == "__main__":
    with create_app().app_context():
        for tabela, chave, campo, contexto in CAMPOS:
            cifrar_tabela(tabela, chave, campo, contexto)
