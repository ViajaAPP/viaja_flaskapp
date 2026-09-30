from datetime import datetime, timezone
from app.services.supabase_service import supabase
from app.services.cache_service import lembrar
from app.models.enums import RequestStatus, TourStatus

@lembrar("passeios")
def _todas_as_notas():
    return supabase.table("tour_review").select("tour_id, rating").execute().data or []

def summary_by_tour(tour_ids=None):
    ids = set(tour_ids) if tour_ids is not None else None
    notas = [n for n in _todas_as_notas() if ids is None or n["tour_id"] in ids]
    totais = {}
    for review in notas:
        soma, quantidade = totais.get(review['tour_id'], (0, 0))
        totais[review['tour_id']] = (soma + review['rating'], quantidade + 1)
    return {tour_id: {"average": round(soma / quantidade, 1), "count": quantidade} for tour_id, (soma, quantidade) in totais.items()}

def list_reviews(tour_id, limit=30):
    reviews = supabase.table("tour_review").select("id, rating, comment, created_at, user_id") \
        .eq("tour_id", tour_id).order("created_at", desc=True).limit(limit).execute().data or []
    user_ids = {review['user_id'] for review in reviews}
    users = {}
    if user_ids:
        response = supabase.table("user").select("user_id, first_name, photo").in_("user_id", list(user_ids)).execute()
        users = {user['user_id']: user for user in response.data or []}
    return [{
        "id": review['id'],
        "rating": review['rating'],
        "comment": review['comment'],
        "created_at": review['created_at'],
        "author": (users.get(review['user_id']) or {}).get('first_name') or "Viajante",
        "author_photo": (users.get(review['user_id']) or {}).get('photo'),
    } for review in reviews]

def instance_to_review(tour_id, user_id):
    agora = datetime.now(timezone.utc)
    instances = supabase.table("tour_instance").select("id, start_time, status").eq("tour_id", tour_id).execute().data or []
    passadas = {
        instance['id'] for instance in instances
        if instance['status'] != TourStatus.CANCELED.value
        and datetime.fromisoformat(instance['start_time'].replace('Z', '+00:00')) < agora
    }
    if not passadas:
        return None
    aceitas = supabase.table("tour_request").select("tour_instance_id").eq("requester_id", user_id) \
        .eq("status", RequestStatus.ACCEPTED.value).in_("tour_instance_id", list(passadas)).execute().data or []
    avaliadas = supabase.table("tour_review").select("tour_instance_id").eq("user_id", user_id).eq("tour_id", tour_id).execute().data or []
    ja_avaliadas = {review['tour_instance_id'] for review in avaliadas}
    pendentes = [request['tour_instance_id'] for request in aceitas if request['tour_instance_id'] not in ja_avaliadas]
    return pendentes[0] if pendentes else None

def create_review(tour_id, instance_id, user_id, rating, comment):
    supabase.table("tour_review").insert({
        "tour_id": tour_id,
        "tour_instance_id": instance_id,
        "user_id": user_id,
        "rating": rating,
        "comment": comment or None,
    }).execute()
