# README — API Flask (`viaja_flaskapp`)

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
- Banco de dados configurado via variáveis de ambiente (ex.: SQLite/PostgreSQL)

---

## Como reproduzir a API em outro computador

## 1) Clonar o projeto
```bash
git clone https://github.com/sweetsoph/viaja_flaskapp.git
cd viaja_flaskapp
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
Criar arquivo `.env` na raiz (exemplo):
```env
SUPABASE_URL=https://pxwjvoztqcdercllisuy.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB4d2p2b3p0cWNkZXJjbGxpc3V5Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTQ4MzE3NCwiZXhwIjoyMDkxMDU5MTc0fQ.n-klIylh0Hli_Vi0ys17URlFiC0ktRLT4NnRyAJ_QtA
NGROK_API_TOKEN=3BxetiqW5pBpL0indCoJmzJCo9E_2jXyKm6AC9fGZmuftdzau
NGROK_WS_TOKEN=3ArdSB4looixxLtCZbbI0g3tOTK_6MeAwdbMKYhtF3ur8Z4Wd
AUTH_CRYPT_KEY=viaja_crypt
```

## 5) Iniciar a API
```bash
python run.py
```
API disponível em: `http://127.0.0.1:5000` ou na URL do Ngrok.

---

## Estrutura sugerida do projeto
```text
viaja_flaskapp/
├─ app/
│  ├─ __init__.py          # factory da aplicação
│  ├─ config.py            # configurações por ambiente
│  ├─ models/              # entidades do banco
│  ├─ routes/              # blueprints/endpoints
│  ├─ services/            # regras de negócio
├─ requirements.txt
└─ README.md
```

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
- **Message Worker (Criado)**: processamento assíncrono de mensagens (ex.: fila de mensagens do chat).

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
