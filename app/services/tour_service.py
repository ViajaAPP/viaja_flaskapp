from datetime import datetime, timezone
from app.services.supabase_service import supabase
from app.models.enums import RequestStatus, RegistrationStatus, TourStatus

USER_PUBLIC_FIELDS = "user_id, first_name, last_name, photo"

def find_tour(tour_id):
    response = supabase.table("tour").select("*").eq("id", tour_id).execute()
    return response.data[0] if response.data else None

def find_tour_instance(tour_id, instance_id):
    response = supabase.table("tour_instance").select("*").eq("id", instance_id).eq("tour_id", tour_id).execute()
    return response.data[0] if response.data else None

def find_address(address_id):
    response = supabase.table("address").select("*").eq("id", address_id).execute()
    return response.data[0] if response.data else None

def find_users(user_ids):
    if not user_ids:
        return {}
    response = supabase.table("user").select(USER_PUBLIC_FIELDS).in_("user_id", list(user_ids)).execute()
    return {user['user_id']: user for user in response.data or []}

def find_or_create_address(address):
    address_response = supabase.table("address").select("id").eq("cep", address.cep).eq("neighborhood", address.neighborhood).eq("street", address.street).eq("number", address.number).execute()
    if address_response.data:
        return address_response.data[0]['id']
    address_insert_response = supabase.table("address").insert(address.model_dump()).execute()
    return address_insert_response.data[0]['id'] if address_insert_response.data else None

def list_tours(created_by_id=None):
    query = supabase.table("tour").select("*, tour_instance(*)")
    if created_by_id is not None:
        query = query.eq("created_by_id", created_by_id)
    return query.order("created_at", desc=True).execute().data or []

def list_tour_instances(tour_id):
    response = supabase.table("tour_instance").select("*").eq("tour_id", tour_id).order("start_time").execute()
    return response.data or []

def list_published_tour_ids():
    response = supabase.table("tour").select("id").eq("published", True).execute()
    return {tour['id'] for tour in response.data or []}

def map_request_status_by_instance(requester_id, instance_ids):
    if not instance_ids:
        return {}
    response = supabase.table("tour_request").select("tour_instance_id, status").eq("requester_id", requester_id).in_("tour_instance_id", instance_ids).execute()
    return {request['tour_instance_id']: request['status'] for request in response.data or []}

def count_accepted_requests(instance_id):
    response = supabase.table("tour_request").select("id", count="exact").eq("tour_instance_id", instance_id).eq("status", RequestStatus.ACCEPTED.value).execute()
    return response.count or 0

def is_instance_open_for_requests(instance):
    start_time = datetime.fromisoformat(instance['start_time'].replace('Z', '+00:00'))
    return (
        instance['status'] == TourStatus.SCHEDULED.value
        and instance['registration'] == RegistrationStatus.OPEN.value
        and start_time > datetime.now(timezone.utc)
    )

def close_registration_if_full(instance):
    if count_accepted_requests(instance['id']) >= instance['max_capacity']:
        supabase.table("tour_instance").update({"registration": RegistrationStatus.FULL.value}).eq("id", instance['id']).execute()
