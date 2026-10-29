from datetime import datetime, timezone
from app.services import supabase_service
from app.services.cnpj_service import buscar_dados_cnpj
from app.services import aviso_service

CNAES = {"GUIDE": [7911200, 7912100], "EVENT_PROMOTER": [8230001]}
NOMES = {"GUIDE": "guia de turismo", "EVENT_PROMOTER": "produtor de eventos"}
CAMPOS = "id, created_at, user_id, role, status, cnpj, review_note, reviewed_at"

class PedidoInvalido(Exception):
    pass

def aprovados(user_id):
    dados = supabase_service.supabase.table("user_role_grant").select("role").eq("user_id", user_id).eq("status", "APPROVED").execute().data or []
    return [d["role"] for d in dados]

def meus(user_id):
    return supabase_service.supabase.table("user_role_grant").select(CAMPOS).eq("user_id", user_id).order("created_at").execute().data or []

def _papel_principal(user_id):
    dados = supabase_service.supabase.table("user").select("role").eq("user_id", user_id).execute().data or []
    return dados[0]["role"] if dados else None

def _admins():
    dados = supabase_service.supabase.table("user").select("user_id").eq("role", "ADMIN").execute().data or []
    return [d["user_id"] for d in dados]

def pedir(user_id, role, cnpj):
    if role not in CNAES:
        raise PedidoInvalido("Esse papel não pode ser pedido.")
    if _papel_principal(user_id) == role:
        raise PedidoInvalido(f"Você já é {NOMES[role]}.")
    cnpj = "".join(filter(str.isdigit, cnpj or ""))
    if len(cnpj) != 14:
        raise PedidoInvalido("Confere o CNPJ: são 14 números.")
    dados = buscar_dados_cnpj(cnpj)
    if dados is None:
        raise PedidoInvalido("Não achamos esse CNPJ. Confere e tenta de novo.")
    if dados.get("cnae_fiscal") not in CNAES[role]:
        raise PedidoInvalido(f"Esse CNPJ não é de {NOMES[role]}.")
    existente = supabase_service.supabase.table("user_role_grant").select(CAMPOS).eq("user_id", user_id).eq("role", role).execute().data or []
    if existente and existente[0]["status"] in ("PENDING", "APPROVED"):
        return existente[0]
    novo = {"user_id": user_id, "role": role, "cnpj": cnpj, "status": "PENDING", "review_note": None, "reviewed_by": None, "reviewed_at": None}
    if existente:
        pedido = supabase_service.supabase.table("user_role_grant").update(novo).eq("id", existente[0]["id"]).execute().data[0]
    else:
        pedido = supabase_service.supabase.table("user_role_grant").insert(novo).execute().data[0]
    aviso_service.criar(_admins(), "papel_para_analise", f"Pedido para ser {NOMES[role]}", "Tem um pedido de papel esperando análise.", "/analise")
    return pedido

def para_analise():
    pedidos = supabase_service.supabase.table("user_role_grant").select(CAMPOS).eq("status", "PENDING").order("created_at").execute().data or []
    ids = {p["user_id"] for p in pedidos}
    pessoas = {}
    if ids:
        dados = supabase_service.supabase.table("user").select("user_id, first_name, last_name, photo, role").in_("user_id", list(ids)).execute().data or []
        pessoas = {d["user_id"]: d for d in dados}
    return [{**p, "user": pessoas.get(p["user_id"])} for p in pedidos]

def buscar(pedido_id):
    dados = supabase_service.supabase.table("user_role_grant").select(CAMPOS).eq("id", pedido_id).execute().data or []
    return dados[0] if dados else None

def analisar(pedido, admin_id, aprovar, motivo=None):
    status = "APPROVED" if aprovar else "REJECTED"
    supabase_service.supabase.table("user_role_grant").update({
        "status": status, "review_note": None if aprovar else motivo,
        "reviewed_by": admin_id, "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", pedido["id"]).execute()
    nome = NOMES[pedido["role"]]
    if aprovar:
        aviso_service.criar([pedido["user_id"]], "papel_aprovado", f"Agora você também é {nome}",
                            "Entre de novo no app para ver as novas opções.", "/perfil")
    else:
        aviso_service.criar([pedido["user_id"]], "papel_recusado", f"Seu pedido para ser {nome} precisa de ajustes",
                            motivo or "Confira os dados e peça de novo.", "/perfil")
