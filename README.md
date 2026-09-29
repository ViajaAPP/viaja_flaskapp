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

## 4) Rodar local, sem nenhum token
Precisa do Docker aberto. O Supabase sobe na sua máquina com o schema e dados de teste.
```bash
npx supabase start
bash scripts/secrets.sh local
python run.py --local
```
- API: `http://localhost:5000` (documentação em `/docs`)
- WebSocket: `ws://localhost:8765`
- Painel do banco: `http://localhost:54323`
- Contas de teste, todas com a senha `viaja123`: `guia@viaja.local`, `viajante@viaja.local` e `admin@viaja.local`

Para zerar o banco e voltar aos dados de teste: `npx supabase db reset`.

No front, `npm start` já aponta para `http://localhost:5000`.

## 5) Rodar com o Supabase e o ngrok de verdade
Os segredos ficam num arquivo privado no Google Drive, o `viaja-backend.env`, e não no repositório. Não precisa de faturamento no Google Cloud. Quem precisar das chaves recebe acesso a esse arquivo pelo próprio Drive.
```bash
gcloud auth login --enable-gdrive-access
bash scripts/secrets.sh pull
python run.py
```
O `pull` escreve o `.env` com `SUPABASE_URL`, `SUPABASE_KEY`, `AUTH_CRYPT_KEY`, `NGROK_API_TOKEN` e `NGROK_WS_TOKEN`. O `.env` nunca vai para o git.

Para trocar um segredo: `bash scripts/secrets.sh set SUPABASE_KEY` (o valor é colado no terminal e não aparece na tela). Para mandar um `.env` inteiro: `bash scripts/secrets.sh push <arquivo>`.

Mudanças no banco ficam em `supabase/migrations`. Para aplicar no Supabase de verdade: `npx supabase link --project-ref <ref>` e depois `npx supabase db push`.

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
