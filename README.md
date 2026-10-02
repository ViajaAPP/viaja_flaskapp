<p align="center">
  <img src="https://raw.githubusercontent.com/ViajaAPP/viaja-front/staging/src/app/pages/welcome/logo.png" width="180" alt="Viajá">
</p>

<h3 align="center">API do Viajá</h3>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Flask-3.1-000000?logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/Supabase-Postgres-3FCF8E?logo=supabase&logoColor=white" alt="Supabase">
  <img src="https://img.shields.io/badge/Pydantic-2-E92063?logo=pydantic&logoColor=white" alt="Pydantic">
  <img src="https://img.shields.io/badge/WebSocket-chat-010101?logo=socketdotio&logoColor=white" alt="WebSocket">
  <img src="https://img.shields.io/badge/Redis-cache-DC382D?logo=redis&logoColor=white" alt="Redis">
  <img src="https://img.shields.io/badge/Docker-banco%20local-2496ED?logo=docker&logoColor=white" alt="Docker">
</p>

## Visão geral
Esta API foi construída com **Flask** e organizada para facilitar:
- execução em outros ambientes;
- evolução de **modelos** e **rotas**;
- separação de responsabilidades por camadas.

---

## Requisitos
- Python **3.9+**
- `pip`
- Git
- Docker e Node.js 20+, para o banco local

---

## Como reproduzir a API em outro computador

## 1) Clonar o projeto
```bash
git clone https://github.com/ViajaAPP/viaja_flaskapp.git
cd viaja_flaskapp
git checkout staging
```

## 2) Criar e ativar ambiente virtual
### Windows (PowerShell)
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Linux/macOS
```bash
python -m venv .venv
source .venv/bin/activate
```

## 3) Instalar dependências
```bash
pip install -r requirements.txt
```

## 4) Configurar variáveis de ambiente
Gerar o `.env` na raiz:
```bash
npx -y supabase start          # banco local
bash scripts/secrets.sh local  # .env do banco local
bash scripts/secrets.sh pull   # .env de produção
```

## 5) Iniciar a API
```bash
python run.py --local  # banco local
python run.py          # produção
```
API disponível em: `http://127.0.0.1:5000` ou na URL do Ngrok.

---

## Estrutura sugerida do projeto
```text
viaja_flaskapp/
├─ app/
│  ├─ __init__.py          # factory da aplicação
│  ├─ models/              # entidades do banco
│  ├─ routes/              # blueprints/endpoints
│  ├─ services/            # regras de negócio
├─ scripts/                # secrets.sh e dados de exemplo
├─ supabase/               # migrations e seed do banco local
├─ config.py               # configurações por ambiente
├─ requirements.txt
└─ README.md
```

---

## Como visualizar as rotas disponíveis
1. Iniciar a API.
2. Acessar a URL informada pelo serviço do NGROK (ex.: `https://abc123.ngrok.io`).
3. Adicionar `/docs` para acessar a documentação interativa (ex.: `https://abc123.ngrok.io/docs`).

Nela, você pode testar os endpoints diretamente pela interface, visualizar os parâmetros esperados e as respostas.

---

## Como adicionar novos modelos

1. Criar arquivo em `app/models/` (ex.: `destino.py`).
2. Definir a classe do modelo.
3. Registrar/importar o modelo onde necessário.

---

## Como adicionar novas rotas

1. Criar blueprint em `app/routes/` (ex.: `destinos.py`).
2. Definir endpoints e métodos HTTP.
3. Registrar blueprint no `create_app()`.

Exemplo:
```python
# app/routes/destinos.py
from flask import Blueprint, jsonify
bp = Blueprint("destinos", __name__, url_prefix="/destinos")

@bp.get("/")
def listar_destinos():
    return jsonify([])
```

Registro:
```python
# app/__init__.py
from app.routes.destinos import bp as destinos_bp
app.register_blueprint(destinos_bp)
```

---

## Serviços Utilizados e Criados

- **Supabase**: banco de dados e autenticação.
- **Ngrok**: exposição local para testes externos.
- **Flask**: framework web leve e flexível.
- **BrasilAPI**: validação de CNPJ para promotores de eventos.
- **Pydantic**: validação e parsing de dados.
- **Redis**: cache das respostas.
- **Photon**: busca de endereço.
- **CidadesBR-API (Criado)**: municípios do Brasil com coordenadas.
- **WebSocket (Criado)**: chat em tempo real.

---

## Design patterns de arquitetura usados

- **Application Factory**: inicialização do Flask via função `create_app()`.
- **Blueprints**: modularização de rotas por domínio.
- **DTO/Schema**: validação e serialização de dados.

---

## Contribuição
1. Criar branch de feature.
2. Implementar com testes.
3. Abrir Pull Request com descrição objetiva.
4. Aguardar revisão.
