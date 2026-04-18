import time
import requests
from typing import Optional
from flask import current_app

def buscar_dados_cnpj(cnpj: str, tentativas: int = 3) -> Optional[dict]:
    cnpj_limpo = "".join(filter(str.isdigit, cnpj))
    url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}"

    for i in range(tentativas):
        try:
            resp = requests.get(url, timeout=5)
            
            if resp.status_code == 200:
                return resp.json()
            
            if resp.status_code == 400:
                current_app.logger.warning(f"CNPJ inválido consultado: {cnpj}")
                return None
            
            # Se for 429 (Too Many Requests) ou 5xx (Erro no servidor deles)
            if i < tentativas - 1:
                time.sleep(2 * (i + 1)) # Backoff exponencial simples
                
        except requests.RequestException as e:
            current_app.logger.error(f"Erro na Brasil API: {e}")
            if i < tentativas - 1:
                time.sleep(2)
                
    return None