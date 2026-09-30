import io
import uuid
from flask import current_app
from PIL import Image, ImageOps, UnidentifiedImageError
from app.services.supabase_service import supabase

BUCKET = "fotos"
TAMANHO_MAXIMO = 5 * 1024 * 1024
LADO_DO_PERFIL = 512
CAPA = (1200, 675)

class FotoInvalida(Exception):
    pass

def _abrir(arquivo):
    conteudo = arquivo.read(TAMANHO_MAXIMO + 1)
    if len(conteudo) > TAMANHO_MAXIMO:
        raise FotoInvalida("A foto pode ter no máximo 5 MB")
    try:
        imagem = Image.open(io.BytesIO(conteudo))
        imagem.load()
    except (UnidentifiedImageError, OSError):
        raise FotoInvalida("Esse arquivo não parece ser uma foto")
    return ImageOps.exif_transpose(imagem).convert("RGB")

def _enviar(imagem, pasta):
    saida = io.BytesIO()
    imagem.save(saida, format="JPEG", quality=85, optimize=True)
    caminho = f"{pasta}/{uuid.uuid4().hex}.jpg"
    supabase.storage.from_(BUCKET).upload(caminho, saida.getvalue(), {"content-type": "image/jpeg"})
    return supabase.storage.from_(BUCKET).get_public_url(caminho).rstrip("?")

def enviar_foto_de_perfil(arquivo, user_id):
    imagem = ImageOps.fit(_abrir(arquivo), (LADO_DO_PERFIL, LADO_DO_PERFIL), Image.LANCZOS)
    return _enviar(imagem, f"usuarios/{user_id}")

def enviar_capa_de_passeio(arquivo, user_id):
    imagem = ImageOps.fit(_abrir(arquivo), CAPA, Image.LANCZOS)
    return _enviar(imagem, f"passeios/{user_id}")

def apagar_foto(url):
    marcador = f"/storage/v1/object/public/{BUCKET}/"
    if not url or marcador not in url:
        return
    caminho = url.split(marcador, 1)[1]
    try:
        supabase.storage.from_(BUCKET).remove([caminho])
    except Exception as e:
        current_app.logger.warning(f"Não foi possível apagar a foto antiga: {e}")
