from datetime import datetime, timedelta, timezone
from flask import current_app
from app.services.supabase_service import supabase

FUSO = timezone(timedelta(hours=-3))

def _data(inicio: str) -> str:
    return datetime.fromisoformat(inicio.replace('Z', '+00:00')).astimezone(FUSO).strftime('%d/%m às %H:%M')

def _primeiro_nome(user_id) -> str:
    dados = supabase.table("user").select("first_name").eq("user_id", user_id).execute().data
    return (dados[0]['first_name'] if dados else '') or 'Alguém'

def criar(user_ids, kind: str, title: str, body: str = None, link: str = None):
    ids = [user_id for user_id in dict.fromkeys(user_ids) if user_id]
    if not ids:
        return
    try:
        supabase.table("notification").insert([
            {"user_id": user_id, "kind": kind, "title": title, "body": body, "link": link} for user_id in ids
        ]).execute()
    except Exception as e:
        current_app.logger.error(f"Erro ao criar aviso: {e}")

def listar(user_id, limite=50):
    return supabase.table("notification").select("id, created_at, kind, title, body, link, read_at") \
        .eq("user_id", user_id).order("created_at", desc=True).limit(limite).execute().data or []

def contar_nao_lidas(user_id) -> int:
    resposta = supabase.table("notification").select("id", count="exact").eq("user_id", user_id).is_("read_at", "null").execute()
    return resposta.count or 0

def marcar_lidas(user_id, ids=None):
    query = supabase.table("notification").update({"read_at": datetime.now(timezone.utc).isoformat()}) \
        .eq("user_id", user_id).is_("read_at", "null")
    if ids:
        query = query.in_("id", ids)
    query.execute()

def pedido_novo(tour, instance, requester_id):
    criar([tour['created_by_id']], "pedido_novo",
          f"{_primeiro_nome(requester_id)} quer ir no seu passeio",
          f"{tour['title']}, {_data(instance['start_time'])}. Responda para a pessoa saber se tem vaga.",
          "/painel")

def reserva_instantanea(tour, instance, requester_id):
    criar([tour['created_by_id']], "reserva_nova",
          f"{_primeiro_nome(requester_id)} reservou uma vaga",
          f"{tour['title']}, {_data(instance['start_time'])}. A vaga já está confirmada.",
          "/painel?aba=agenda")
    criar([requester_id], "pedido_aceito", "Sua vaga está confirmada!",
          f"{tour['title']}, {_data(instance['start_time'])}. O chat do grupo já está aberto.",
          f"/passeio/{tour['id']}")

def pedido_respondido(tour, instance, requester_id, aceito: bool):
    if aceito:
        criar([requester_id], "pedido_aceito", "Sua vaga está confirmada!",
              f"{tour['title']}, {_data(instance['start_time'])}. O chat do grupo já está aberto.",
              f"/passeio/{tour['id']}")
    else:
        criar([requester_id], "pedido_recusado", "O guia não conseguiu confirmar sua vaga",
              f"{tour['title']}, {_data(instance['start_time'])}. Veja outras datas ou outros passeios.",
              f"/passeio/{tour['id']}")

def data_cancelada(tour, instance):
    aceitos = supabase.table("tour_request").select("requester_id").eq("tour_instance_id", instance['id']) \
        .in_("status", ["ACCEPTED", "PENDING"]).execute().data or []
    criar([pedido['requester_id'] for pedido in aceitos], "data_cancelada", "Uma data do seu passeio foi cancelada",
          f"{tour['title']}, {_data(instance['start_time'])}. Veja se tem outra data que combine com você.",
          f"/passeio/{tour['id']}")

def avaliacao_nova(tour, autor_id, nota: int):
    criar([tour['created_by_id']], "avaliacao_nova", f"{_primeiro_nome(autor_id)} avaliou seu passeio com {nota} de 5",
          tour['title'], f"/passeio/{tour['id']}")
