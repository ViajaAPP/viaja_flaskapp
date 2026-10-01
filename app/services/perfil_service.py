from collections import Counter
from datetime import datetime, timezone
from app.services import supabase_service, busca_service, review_service, resposta_service, evento_service

LIMITE_DE_AVALIACOES = 10

def _pessoa(user_id):
    dados = (
        supabase_service.supabase.table("user")
        .select("user_id, first_name, last_name, photo, role, bio, created_at")
        .eq("user_id", user_id)
        .execute()
        .data
    )
    return dados[0] if dados else None

def _titulos(tour_ids):
    if not tour_ids:
        return {}
    dados = supabase_service.supabase.table("tour").select("id, title, photo").in_("id", list(tour_ids)).execute().data or []
    return {t["id"]: t for t in dados}

def _autores(user_ids):
    if not user_ids:
        return {}
    dados = supabase_service.supabase.table("user").select("user_id, first_name, photo").in_("user_id", list(user_ids)).execute().data or []
    return {u["user_id"]: u for u in dados}

def _avaliacoes_recebidas(tour_ids):
    if not tour_ids:
        return []
    dados = (
        supabase_service.supabase.table("tour_review")
        .select("id, tour_id, user_id, rating, comment, created_at")
        .in_("tour_id", list(tour_ids))
        .order("created_at", desc=True)
        .limit(LIMITE_DE_AVALIACOES)
        .execute()
        .data or []
    )
    autores = _autores({a["user_id"] for a in dados})
    passeios = _titulos({a["tour_id"] for a in dados})
    return [{
        "id": a["id"],
        "rating": a["rating"],
        "comment": a["comment"],
        "created_at": a["created_at"],
        "tour_id": a["tour_id"],
        "tour_title": (passeios.get(a["tour_id"]) or {}).get("title"),
        "author_id": a["user_id"],
        "author": (autores.get(a["user_id"]) or {}).get("first_name") or "Viajante",
        "author_photo": (autores.get(a["user_id"]) or {}).get("photo"),
    } for a in dados]

def _avaliacoes_escritas(user_id):
    dados = (
        supabase_service.supabase.table("tour_review")
        .select("id, tour_id, rating, comment, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(LIMITE_DE_AVALIACOES)
        .execute()
        .data or []
    )
    passeios = _titulos({a["tour_id"] for a in dados})
    return [{
        "id": a["id"],
        "rating": a["rating"],
        "comment": a["comment"],
        "created_at": a["created_at"],
        "tour_id": a["tour_id"],
        "tour_title": (passeios.get(a["tour_id"]) or {}).get("title"),
        "tour_photo": (passeios.get(a["tour_id"]) or {}).get("photo"),
    } for a in dados]

def _nota_geral(tour_ids):
    notas = review_service.summary_by_tour(tour_ids).values()
    total = sum(n["count"] for n in notas)
    if not total:
        return None
    return {"average": round(sum(n["average"] * n["count"] for n in notas) / total, 1), "count": total}

def _agora():
    return datetime.now(timezone.utc).isoformat()

def _numeros_de_viajante(user_id):
    db = supabase_service.supabase
    pedidos = (
        db.table("tour_request")
        .select("tour_instance(start_time, status, tour(address(city, uf)))")
        .eq("requester_id", user_id)
        .eq("status", "ACCEPTED")
        .execute()
        .data or []
    )
    agora = _agora()
    feitas = [
        p["tour_instance"] for p in pedidos
        if p.get("tour_instance") and p["tour_instance"]["start_time"] < agora and p["tour_instance"]["status"] != "CANCELLED"
    ]
    presencas = (
        db.table("event_attendance")
        .select("event(start_time, status, address(city, uf))")
        .eq("user_id", user_id)
        .execute()
        .data or []
    )
    eventos = [
        p["event"] for p in presencas
        if p.get("event") and p["event"]["start_time"] < agora and p["event"]["status"] in ("PUBLISHED", "DONE")
    ]
    cidades = Counter()
    for viagem in feitas:
        endereco = ((viagem.get("tour") or {}).get("address")) or {}
        if endereco.get("city"):
            cidades[(endereco["city"], endereco.get("uf"))] += 1
    for evento in eventos:
        endereco = evento.get("address") or {}
        if endereco.get("city"):
            cidades[(endereco["city"], endereco.get("uf"))] += 1
    return {
        "trips": len(feitas),
        "events_attended": len(eventos),
        "cities": [{"city": c, "uf": uf, "count": n} for (c, uf), n in cidades.most_common()],
    }

def _numeros_de_guia(tour_ids, ativos):
    if not tour_ids:
        return None
    db = supabase_service.supabase
    instancias = db.table("tour_instance").select("id, start_time, status").in_("tour_id", list(tour_ids)).execute().data or []
    agora = _agora()
    realizadas = [i["id"] for i in instancias if i["start_time"] < agora and i["status"] != "CANCELLED"]
    guiados = 0
    if realizadas:
        guiados = len(
            db.table("tour_request").select("id").in_("tour_instance_id", realizadas).eq("status", "ACCEPTED").execute().data or []
        )
    return {"travelers_guided": guiados, "tours_done": len(realizadas), "tours_active": ativos}

def _numeros_de_produtor(user_id, proximos):
    db = supabase_service.supabase
    eventos = db.table("event").select("id, start_time, status").eq("organizer_id", user_id).execute().data or []
    if not eventos:
        return None
    agora = _agora()
    realizados = [e["id"] for e in eventos if e["start_time"] < agora and e["status"] in ("PUBLISHED", "DONE")]
    pessoas = 0
    if realizados:
        pessoas = len(db.table("event_attendance").select("user_id").in_("event_id", realizados).execute().data or [])
    return {"events_done": len(realizados), "people_attended": pessoas, "events_upcoming": proximos}

def perfil_publico(user_id, quem_ve_id):
    pessoa = _pessoa(user_id)
    if not pessoa:
        return None

    passeios = [p for p in busca_service.buscar_passeios(quem_ve_id) if p.get("guideId") == user_id]
    todos_os_passeios = {
        t["id"] for t in supabase_service.supabase.table("tour").select("id").eq("created_by_id", user_id).execute().data or []
    }
    eventos = [e for e in evento_service.listar_publicados(quem_ve_id) if (e.get("organizer") or {}).get("user_id") == user_id]

    escritas = _avaliacoes_escritas(user_id)
    viajante = _numeros_de_viajante(user_id)
    viajante["reviews_written"] = (
        supabase_service.supabase.table("tour_review").select("id", count="exact").eq("user_id", user_id).limit(1).execute().count or 0
    )
    tem_cara_de_viajante = pessoa["role"] == "TOURIST" or viajante["trips"] or viajante["events_attended"]

    return {
        "user_id": pessoa["user_id"],
        "first_name": pessoa["first_name"],
        "last_name": pessoa["last_name"],
        "photo": pessoa["photo"],
        "role": pessoa["role"],
        "bio": pessoa.get("bio"),
        "member_since": pessoa["created_at"],
        "is_me": pessoa["user_id"] == quem_ve_id,
        "rating": _nota_geral(todos_os_passeios),
        "response_time": resposta_service.tempo_de_resposta(user_id) if todos_os_passeios else None,
        "tours": passeios,
        "events": eventos,
        "reviews_received": _avaliacoes_recebidas(todos_os_passeios),
        "reviews_written": escritas,
        "stats": {
            "traveler": viajante if tem_cara_de_viajante else None,
            "guide": _numeros_de_guia(todos_os_passeios, len(passeios)),
            "promoter": _numeros_de_produtor(user_id, len(eventos)),
        },
    }
