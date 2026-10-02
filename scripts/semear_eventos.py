import argparse
import json
import os
import random
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from semear_passeios import create_app, credito, enviar_foto, garantir_viajantes, slug, supabase_service, usuario

PRODUTORA = "produtor@viaja.local"
ADMIN = "admin@viaja.local"
FUSO = timezone(timedelta(hours=-3))

def foto_com_paciencia(sb, url, caminho):
    for espera in (0, 20, 45, 90):
        time.sleep(espera)
        try:
            return enviar_foto(sb, url, caminho)
        except requests.HTTPError as erro:
            if erro.response is None or erro.response.status_code != 429:
                raise
    raise SystemExit(f"O Wikimedia não liberou a foto {url}. Tente de novo daqui a pouco.")

def garantir_endereco(sb, item):
    endereco = item["address"]
    busca = sb.table("address").select("id").eq("city", item["city"]).eq("street", endereco["street"]) \
        .eq("neighborhood", endereco["neighborhood"]).eq("number", endereco["number"]).execute().data
    if busca:
        sb.table("address").update({"lat": item["lat"], "lon": item["lon"]}).eq("id", busca[0]["id"]).execute()
        return busca[0]["id"]
    return sb.table("address").insert({**endereco, "cep": None, "uf": "SP", "city": item["city"], "lat": item["lat"], "lon": item["lon"]}).execute().data[0]["id"]

def horario(item):
    hora, minuto = (int(parte) for parte in item["hora"].split(":"))
    dia = datetime.now(FUSO) + timedelta(days=item["dias"])
    inicio = dia.replace(hour=hora, minute=minuto, second=0, microsecond=0)
    return inicio, inicio + timedelta(hours=item["duracao_horas"])

def main():
    parser = argparse.ArgumentParser(description="Semeia eventos de exemplo com fotos no bucket e gente confirmada.")
    parser.add_argument("--arquivo", default="supabase/dados/eventos.json")
    args = parser.parse_args()

    senha = os.getenv("CONTAS_TESTE_SENHA")
    local = "127.0.0.1" in (os.getenv("SUPABASE_URL") or "") or "localhost" in (os.getenv("SUPABASE_URL") or "")
    if not senha and not local:
        sys.exit("Defina CONTAS_TESTE_SENHA para criar as contas de teste fora do banco local.")

    create_app()
    sb = supabase_service.supabase
    produtora_id = usuario(sb, PRODUTORA)
    if not produtora_id:
        sys.exit(f"A conta {PRODUTORA} não existe nesse banco.")
    admin_id = usuario(sb, ADMIN)
    viajantes = garantir_viajantes(sb, senha or "viaja123")
    sorteio = random.Random(7)

    for item in json.load(open(args.arquivo, encoding="utf-8")):
        inicio, fim = horario(item)
        campos = {
            "organizer_id": produtora_id, "title": item["title"], "description": item["description"],
            "start_time": inicio.isoformat(), "end_time": fim.isoformat(), "place_name": item["place_name"],
            "address_id": garantir_endereco(sb, item), "price": item["price"], "capacity": item["capacity"],
            "photo": foto_com_paciencia(sb, item["image_url"], f"eventos/exemplos/{slug(item['title'])}.jpg"),
            "photo_credit": credito(item), "status": "PUBLISHED", "review_note": None,
            "reviewed_by": admin_id, "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }
        existentes = sb.table("event").select("id").eq("title", item["title"]).execute().data
        if existentes:
            evento_id = existentes[0]["id"]
            sb.table("event").update(campos).eq("id", evento_id).execute()
        else:
            evento_id = sb.table("event").insert(campos).execute().data[0]["id"]
        confirmados = {p["user_id"] for p in sb.table("event_attendance").select("user_id").eq("event_id", evento_id).execute().data or []}
        for user_id in sorteio.sample(viajantes, min(item.get("vao", 0), len(viajantes))):
            if user_id not in confirmados:
                sb.table("event_attendance").insert({"event_id": evento_id, "user_id": user_id}).execute()
        print(f"  . {item['city']}: {item['title']}")
        time.sleep(2)

    print("Pronto.")

if __name__ == "__main__":
    main()
