#!/usr/bin/env bash
set -euo pipefail

PROJETO="${GCP_PROJECT:-viajaapp}"
CONFIGURACAO_GCLOUD="${GCLOUD_CONFIG:-viaja}"
ARQUIVO_ENV="${ENV_FILE:-.env}"
URL_WS_LOCAL="ws://localhost:8765"

SEGREDOS=(
  "SUPABASE_URL:supabase-url"
  "SUPABASE_KEY:supabase-key"
  "AUTH_CRYPT_KEY:auth-crypt-key"
  "NGROK_API_TOKEN:ngrok-api-token"
  "NGROK_WS_TOKEN:ngrok-ws-token"
)

ok()    { printf '  . %s\n' "$1"; }
aviso() { printf '  ! %s\n' "$1" >&2; }

usa_configuracao_do_projeto() {
  if gcloud config configurations describe "$CONFIGURACAO_GCLOUD" >/dev/null 2>&1; then
    export CLOUDSDK_ACTIVE_CONFIG_NAME="$CONFIGURACAO_GCLOUD"
  fi
}

gera_chave() {
  python -c "import secrets; print(secrets.token_urlsafe(48), end='')"
}

nome_do_segredo() {
  local variavel="$1" par
  for par in "${SEGREDOS[@]}"; do
    if [[ "${par%%:*}" == "$variavel" || "${par##*:}" == "$variavel" ]]; then
      printf '%s' "${par##*:}"
      return
    fi
  done
  aviso "Não conheço '$variavel'. Opções: ${SEGREDOS[*]}"
  exit 1
}

tem_valor() {
  gcloud secrets versions describe latest --secret="$1" --project="$PROJETO" >/dev/null 2>&1
}

garante_segredo() {
  gcloud secrets describe "$1" --project="$PROJETO" >/dev/null 2>&1 && return
  gcloud secrets create "$1" --project="$PROJETO" --replication-policy=automatic >/dev/null
}

apaga_versoes_antigas() {
  local segredo="$1" ultima versao
  ultima="$(gcloud secrets versions list "$segredo" --project="$PROJETO" --filter="state=ENABLED" --sort-by="~createTime" --limit=1 --format="value(name.basename())")"
  for versao in $(gcloud secrets versions list "$segredo" --project="$PROJETO" --filter="state!=DESTROYED" --format="value(name.basename())"); do
    [[ "$versao" == "$ultima" ]] && continue
    gcloud secrets versions destroy "$versao" --secret="$segredo" --project="$PROJETO" --quiet >/dev/null
  done
}

grava_do_stdin() {
  local segredo="$1"
  garante_segredo "$segredo"
  gcloud secrets versions add "$segredo" --project="$PROJETO" --data-file=- >/dev/null
  apaga_versoes_antigas "$segredo"
  ok "$segredo gravado"
}

escreve_env() {
  local temporario
  temporario="$(mktemp)"
  cat > "$temporario"
  chmod 600 "$temporario"
  mv "$temporario" "$ARQUIVO_ENV"
  ok "$ARQUIVO_ENV escrito"
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
  local par variavel segredo valor
  {
    for par in "${SEGREDOS[@]}"; do
      variavel="${par%%:*}"
      segredo="${par##*:}"
      if ! valor="$(gcloud secrets versions access latest --secret="$segredo" --project="$PROJETO" 2>/dev/null)"; then
        aviso "$segredo ainda não tem valor no projeto $PROJETO"
        continue
      fi
      printf '%s=%s\n' "$variavel" "$valor"
    done
  } | escreve_env
}

comando_set() {
  usa_configuracao_do_projeto
  local segredo valor
  segredo="$(nome_do_segredo "${1:?Informe qual: ${SEGREDOS[*]}}")"
  printf 'Cole o valor de %s e tecle Enter: ' "$segredo"
  read -rs valor
  echo
  printf '%s' "$valor" | grava_do_stdin "$segredo"
  unset valor
}

comando_gerar() {
  usa_configuracao_do_projeto
  if tem_valor auth-crypt-key; then
    ok "auth-crypt-key já tem valor. Trocar desloga todo mundo; use 'set AUTH_CRYPT_KEY' se for isso mesmo"
    return
  fi
  gera_chave | grava_do_stdin auth-crypt-key
}

case "${1:-}" in
  local) comando_local ;;
  pull)  comando_pull ;;
  set)   comando_set "${2:-}" ;;
  gerar) comando_gerar ;;
  *)
    echo "Uso: scripts/secrets.sh local | pull | set <NOME> | gerar"
    echo "  local  escreve o .env apontando para o Supabase local, sem tokens"
    echo "  pull   escreve o .env com os segredos do Secret Manager ($PROJETO)"
    echo "  set    grava um segredo novo e apaga as versões antigas"
    echo "  gerar  cria a AUTH_CRYPT_KEY aleatória no Secret Manager"
    exit 1
    ;;
esac
