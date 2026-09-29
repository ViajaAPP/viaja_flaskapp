#!/usr/bin/env bash
set -euo pipefail

CONFIGURACAO_GCLOUD="${GCLOUD_CONFIG:-viaja}"
NOME_NO_DRIVE="${DRIVE_FILE:-viaja-backend.env}"
ARQUIVO_ENV="${ENV_FILE:-.env}"
URL_WS_LOCAL="ws://localhost:8765"
DRIVE="https://www.googleapis.com/drive/v3/files"
DRIVE_UPLOAD="https://www.googleapis.com/upload/drive/v3/files"
VARIAVEIS="SUPABASE_URL SUPABASE_KEY AUTH_CRYPT_KEY NGROK_API_TOKEN NGROK_WS_TOKEN"

ok()    { printf '  . %s\n' "$1"; }
aviso() { printf '  ! %s\n' "$1" >&2; }

usa_configuracao_do_projeto() {
  if gcloud config configurations describe "$CONFIGURACAO_GCLOUD" >/dev/null 2>&1; then
    export CLOUDSDK_ACTIVE_CONFIG_NAME="$CONFIGURACAO_GCLOUD"
  fi
}

token() {
  gcloud auth print-access-token 2>/dev/null || {
    aviso "Sem login no Google. Rode: gcloud auth login --enable-gdrive-access"
    exit 1
  }
}

drive() {
  curl -sS --fail-with-body -H "Authorization: Bearer $(token)" "$@"
}

id_do_arquivo() {
  drive -G "$DRIVE" \
    --data-urlencode "q=name = '$NOME_NO_DRIVE' and trashed = false" \
    --data-urlencode "fields=files(id)" \
    | python -c "import json, sys; arquivos = json.load(sys.stdin)['files']; print(arquivos[0]['id'] if arquivos else '', end='')"
}

cria_arquivo() {
  drive -X POST "$DRIVE?fields=id" -H "Content-Type: application/json" \
    -d "{\"name\": \"$NOME_NO_DRIVE\", \"mimeType\": \"text/plain\"}" \
    | python -c "import json, sys; print(json.load(sys.stdin)['id'], end='')"
}

baixa_do_drive() {
  local id
  id="$(id_do_arquivo)"
  if [[ -z "$id" ]]; then
    aviso "Não achei '$NOME_NO_DRIVE' no seu Drive. Suba com: scripts/secrets.sh push <arquivo>"
    exit 1
  fi
  drive "$DRIVE/$id?alt=media"
}

sobe_para_o_drive() {
  local id
  id="$(id_do_arquivo)"
  [[ -n "$id" ]] || id="$(cria_arquivo)"
  drive -X PATCH "$DRIVE_UPLOAD/$id?uploadType=media" -H "Content-Type: text/plain" --data-binary @- >/dev/null
  ok "$NOME_NO_DRIVE atualizado no Drive"
}

gera_chave() {
  python -c "import secrets; print(secrets.token_urlsafe(48), end='')"
}

escreve_env() {
  local temporario
  temporario="$(mktemp)"
  cat > "$temporario"
  chmod 600 "$temporario"
  mv "$temporario" "$ARQUIVO_ENV"
  ok "$ARQUIVO_ENV escrito"
}

troca_variavel() {
  local variavel="$1" valor="$2"
  VARIAVEL="$variavel" VALOR="$valor" python -c "
import os, sys
variavel, valor = os.environ['VARIAVEL'], os.environ['VALOR']
linhas = [linha for linha in sys.stdin.read().splitlines() if not linha.startswith(variavel + '=')]
linhas.append(variavel + '=' + valor)
print('\n'.join(linha for linha in linhas if linha.strip()))
"
}

confere_variavel() {
  [[ " $VARIAVEIS " == *" $1 "* ]] && return
  aviso "Não conheço '$1'. Opções: $VARIAVEIS"
  exit 1
}

valor_atual() {
  [[ -f "$ARQUIVO_ENV" ]] || return 0
  grep -E "^$1=" "$ARQUIVO_ENV" | head -1 | cut -d= -f2- || true
}

comando_local() {
  local status url chave auth
  status="$(npx -y supabase@latest status -o env)"
  url="$(printf '%s\n' "$status" | grep -E '^API_URL=' | cut -d= -f2- | tr -d '"')"
  chave="$(printf '%s\n' "$status" | grep -E '^SERVICE_ROLE_KEY=' | cut -d= -f2- | tr -d '"')"
  if [[ -z "$url" || -z "$chave" ]]; then
    aviso "O Supabase local não está rodando. Rode: npx supabase start"
    exit 1
  fi
  auth="$(valor_atual AUTH_CRYPT_KEY)"
  [[ -n "$auth" ]] || auth="$(gera_chave)"
  printf 'SUPABASE_URL=%s\nSUPABASE_KEY=%s\nAUTH_CRYPT_KEY=%s\nPUBLIC_URL_WS=%s\n' \
    "$url" "$chave" "$auth" "$URL_WS_LOCAL" | escreve_env
}

comando_pull() {
  usa_configuracao_do_projeto
  baixa_do_drive | escreve_env
}

comando_push() {
  usa_configuracao_do_projeto
  local arquivo="${1:?Informe o arquivo .env que vai para o Drive}"
  [[ -f "$arquivo" ]] || { aviso "Arquivo '$arquivo' não existe"; exit 1; }
  sobe_para_o_drive < "$arquivo"
}

comando_set() {
  usa_configuracao_do_projeto
  local variavel="${1:?Informe qual: $VARIAVEIS}" valor atual
  confere_variavel "$variavel"
  printf 'Cole o valor de %s e tecle Enter: ' "$variavel"
  read -rs valor
  echo
  atual="$(baixa_do_drive 2>/dev/null || true)"
  printf '%s' "$atual" | troca_variavel "$variavel" "$valor" | sobe_para_o_drive
  unset valor atual
}

comando_gerar() {
  usa_configuracao_do_projeto
  local atual
  atual="$(baixa_do_drive 2>/dev/null || true)"
  if printf '%s\n' "$atual" | grep -qE '^AUTH_CRYPT_KEY=.+'; then
    ok "AUTH_CRYPT_KEY já tem valor. Trocar desloga todo mundo; use 'set AUTH_CRYPT_KEY' se for isso mesmo"
    return
  fi
  printf '%s' "$atual" | troca_variavel AUTH_CRYPT_KEY "$(gera_chave)" | sobe_para_o_drive
  unset atual
}

case "${1:-}" in
  local) comando_local ;;
  pull)  comando_pull ;;
  push)  comando_push "${2:-}" ;;
  set)   comando_set "${2:-}" ;;
  gerar) comando_gerar ;;
  *)
    echo "Uso: scripts/secrets.sh local | pull | push <arquivo> | set <NOME> | gerar"
    echo "  local  escreve o .env apontando para o Supabase local, sem tokens"
    echo "  pull   escreve o .env com o arquivo $NOME_NO_DRIVE do seu Google Drive"
    echo "  push   manda um .env inteiro para o Drive"
    echo "  set    troca um valor no arquivo do Drive"
    echo "  gerar  cria a AUTH_CRYPT_KEY aleatória no arquivo do Drive"
    exit 1
    ;;
esac
