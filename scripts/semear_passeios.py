import argparse
import io
import json
import os
import random
import sys
import unicodedata
from datetime import datetime, timedelta, timezone

import bcrypt
import requests
from PIL import Image, ImageOps

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
import app.services.supabase_service as supabase_service

BUCKET = "fotos"
CAPA = (1200, 675)
GUIA = "guia@viaja.local"
CABECALHO = {"User-Agent": "Viaja/1.0 (seed de exemplos; contato pelo repositorio ViajaAPP)"}
VIAJANTES = [
    ("Marina", "Alves"), ("Rafael", "Souza"), ("Beatriz", "Lima"), ("Thiago", "Rocha"),
    ("Camila", "Nunes"), ("Lucas", "Prado"), ("Juliana", "Mota"), ("Pedro", "Farias"),
]

def slug(texto):
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return "-".join("".join(c if c.isalnum() else " " for c in texto.lower()).split())[:60]

def enviar_foto(sb, url, caminho):
    resposta = requests.get(url, headers=CABECALHO, timeout=60)
    resposta.raise_for_status()
    imagem = ImageOps.exif_transpose(Image.open(io.BytesIO(resposta.content))).convert("RGB")
    imagem = ImageOps.fit(imagem, CAPA, Image.LANCZOS)
    saida = io.BytesIO()
    imagem.save(saida, format="JPEG", quality=85, optimize=True)
    sb.storage.from_(BUCKET).upload(caminho, saida.getvalue(), {"content-type": "image/jpeg", "upsert": "true"})
    return sb.storage.from_(BUCKET).get_public_url(caminho).rstrip("?")

def credito(item):
    partes = [item.get("image_author"), item.get("image_license"), "Wikimedia Commons"]
    return ", ".join(p for p in partes if p)

def usuario(sb, email):
    dados = sb.table("user").select("user_id").eq("email", email).execute().data
    return dados[0]["user_id"] if dados else None

def garantir_viajantes(sb, senha):
    ids = []
    senha_hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
    for i, (nome, sobrenome) in enumerate(VIAJANTES, start=1):
        email = f"viajante{i}@viaja.local"
        user_id = usuario(sb, email)
        if not user_id:
            user_id = sb.table("user").insert({
                "username": f"viajante{i}", "email": email, "password": senha_hash,
                "first_name": nome, "last_name": sobrenome, "phone": f"139900000{i:02d}",
                "role": "TOURIST", "photo": "",
            }).execute().data[0]["user_id"]
        ids.append(user_id)
    return ids

def garantir_endereco(sb, item):
    endereco = item["address"]
    busca = sb.table("address").select("id").eq("cep", endereco["cep"]).eq("neighborhood", endereco["neighborhood"]) \
        .eq("street", endereco["street"]).eq("number", endereco["number"]).execute().data
    campos = {**endereco, "uf": "SP", "city": item["city"], "lat": item["lat"], "lon": item["lon"]}
    if busca:
        sb.table("address").update({"lat": item["lat"], "lon": item["lon"], "city": item["city"]}).eq("id", busca[0]["id"]).execute()
        return busca[0]["id"]
    return sb.table("address").insert(campos).execute().data[0]["id"]

def garantir_datas(sb, tour_id, vagas):
    agora = datetime.now(timezone.utc)
    existentes = sb.table("tour_instance").select("id, start_time, status").eq("tour_id", tour_id).execute().data or []
    futuras = [i for i in existentes if datetime.fromisoformat(i["start_time"].replace("Z", "+00:00")) > agora]
    passadas = [i for i in existentes if i["status"] == "DONE"]
    for dias in (6, 13, 27)[len(futuras):]:
        sb.table("tour_instance").insert({
            "tour_id": tour_id, "start_time": (agora + timedelta(days=dias)).replace(hour=12, minute=0, second=0, microsecond=0).isoformat(),
            "max_capacity": vagas, "status": "SCHEDULED", "registration": "OPEN",
        }).execute()
    if passadas:
        return passadas[0]["id"]
    return sb.table("tour_instance").insert({
        "tour_id": tour_id, "start_time": (agora - timedelta(days=12)).replace(hour=12, minute=0, second=0, microsecond=0).isoformat(),
        "max_capacity": vagas, "status": "DONE", "registration": "CLOSED",
    }).execute().data[0]["id"]

def garantir_popularidade(sb, tour_id, passada_id, viajantes, item, sorteio):
    curtidas = min(item.get("curtidas", 0), len(viajantes))
    pedidos = min(item.get("pedidos", 0), len(viajantes))
    avaliacoes = item.get("avaliacoes", [])[:len(viajantes)]
    for user_id in sorteio.sample(viajantes, curtidas):
        if not sb.table("favorite_tour").select("tour_id").eq("user_id", user_id).eq("tour_id", tour_id).execute().data:
            sb.table("favorite_tour").insert({"user_id": user_id, "tour_id": tour_id}).execute()
    proxima = sb.table("tour_instance").select("id").eq("tour_id", tour_id).eq("status", "SCHEDULED").order("start_time").limit(1).execute().data
    for user_id in sorteio.sample(viajantes, pedidos):
        if proxima and not sb.table("tour_request").select("id").eq("tour_instance_id", proxima[0]["id"]).eq("requester_id", user_id).execute().data:
            sb.table("tour_request").insert({"tour_instance_id": proxima[0]["id"], "requester_id": user_id, "status": "PENDING"}).execute()
    for user_id, avaliacao in zip(sorteio.sample(viajantes, len(avaliacoes)), avaliacoes):
        if not sb.table("tour_request").select("id").eq("tour_instance_id", passada_id).eq("requester_id", user_id).execute().data:
            sb.table("tour_request").insert({"tour_instance_id": passada_id, "requester_id": user_id, "status": "ACCEPTED"}).execute()
        if not sb.table("tour_review").select("id").eq("tour_instance_id", passada_id).eq("user_id", user_id).execute().data:
            sb.table("tour_review").insert({
                "tour_id": tour_id, "tour_instance_id": passada_id, "user_id": user_id,
                "rating": avaliacao["nota"], "comment": avaliacao.get("comentario"),
            }).execute()

def main():
    parser = argparse.ArgumentParser(description="Semeia passeios de exemplo com fotos no bucket, datas, curtidas, pedidos e avaliações.")
    parser.add_argument("--arquivo", default="supabase/dados/passeios.json")
    parser.add_argument("--sem-fotos", action="store_true")
    args = parser.parse_args()

    senha = os.getenv("CONTAS_TESTE_SENHA")
    local = "127.0.0.1" in (os.getenv("SUPABASE_URL") or "") or "localhost" in (os.getenv("SUPABASE_URL") or "")
    if not senha and not local:
        sys.exit("Defina CONTAS_TESTE_SENHA para criar as contas de teste fora do banco local.")
    senha = senha or "viaja123"

    create_app()
    sb = supabase_service.supabase
    guia_id = usuario(sb, GUIA)
    if not guia_id:
        sys.exit(f"A conta {GUIA} não existe nesse banco.")

    itens = json.load(open(args.arquivo, encoding="utf-8"))
    viajantes = garantir_viajantes(sb, senha)
    sorteio = random.Random(42)
    resumo = {"criados": 0, "atualizados": 0, "fora_do_ar": 0}

    for item in itens:
        existentes = sb.table("tour").select("id").eq("title", item.get("titulo_antigo") or item["title"]).execute().data
        if item["status"] == "remover":
            for tour in existentes:
                sb.table("tour").update({"published": False}).eq("id", tour["id"]).execute()
                resumo["fora_do_ar"] += 1
            continue

        campos = {
            "title": item["title"], "description": item["description"], "price": item["price"],
            "estimated_duration_minutes": item["estimated_duration_minutes"], "meeting_point": item["meeting_point"],
            "address_id": garantir_endereco(sb, item), "published": True,
        }
        if not item.get("image_url"):
            campos["photo"] = None
            campos["photo_credit"] = None
        elif not args.sem_fotos:
            campos["photo"] = enviar_foto(sb, item["image_url"], f"passeios/exemplos/{slug(item['title'])}.jpg")
            campos["photo_credit"] = credito(item)

        if existentes:
            tour_id = existentes[0]["id"]
            sb.table("tour").update(campos).eq("id", tour_id).execute()
            resumo["atualizados"] += 1
        else:
            campos.setdefault("photo", item.get("image_url"))
            tour_id = sb.table("tour").insert({**campos, "created_by_id": guia_id}).execute().data[0]["id"]
            resumo["criados"] += 1

        if not args.sem_fotos:
            atuais = {foto["url"] for foto in sb.table("tour_photo").select("url").eq("tour_id", tour_id).execute().data or []}
            for posicao, extra in enumerate(item.get("galeria", [])):
                url = enviar_foto(sb, extra["image_url"], f"passeios/exemplos/{slug(item['title'])}-{posicao + 1}.jpg")
                if url not in atuais:
                    sb.table("tour_photo").insert({"tour_id": tour_id, "url": url, "credit": credito(extra), "position": posicao}).execute()

        passada_id = garantir_datas(sb, tour_id, item.get("vagas", 12))
        garantir_popularidade(sb, tour_id, passada_id, viajantes, item, sorteio)
        print(f"  . {item['city']}: {item['title']}")

    print(f"Pronto: {resumo['criados']} criados, {resumo['atualizados']} atualizados, {resumo['fora_do_ar']} tirados do ar.")

if __name__ == "__main__":
    main()
