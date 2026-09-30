# README — API Flask (`viaja_flaskapp`)

## Grupo
- Daniel Ferreira Pinheiro da Silva
- Érika Maria de Sousa
- Giovanna Nassar Lara Santos
- Marcos Rebouças Duarte da Silva
- Sophia Verardo de Araújo

## Visão geral
Esta API foi construída com **Flask** e organizada para facilitar:
- execução em outros ambientes;
- evolução de **modelos** e **rotas**;
- separação de responsabilidades por camadas.

---

## Requisitos
- Python **3.9+**
- `pip`
- Git (no Windows, use o Git Bash para rodar os scripts `.sh`)
- Node.js, para o `npx supabase`
- Docker, para rodar o banco local
- Google Cloud SDK (`gcloud`), para baixar as chaves de produção: https://cloud.google.com/sdk/docs/install

---

## O que tem de novo na `staging`
A `staging` é a versão que está funcionando. Em relação à `main`:

- **Papéis e permissões**: `TOURIST`, `GUIDE`, `EVENT_PROMOTER` e o novo `ADMIN`. A conferência de papel fica no decorator `role_required` e a de dono do passeio em `is_tour_owner` e `can_moderate_tour` (`app/utils/auth.py`). Ninguém se cadastra como `ADMIN` pelo app.
- **Gestão de passeios pelo guia** (`app/routes/tour.py`):
  - `GET /tour/mine`: os passeios do guia (o admin vê todos)
  - `GET /tour/<id>`: detalhe com endereço, guia e datas; rascunho só aparece para o dono e o admin
  - `PATCH /tour/<id>`: editar (só o dono)
  - `PATCH /tour/<id>/publish`: publicar ou tirar do ar (dono ou admin)
  - `PATCH /tour/<id>/instance/<iid>`: vagas, status e se a data está recebendo pedidos
- **Pedidos de vaga** (`app/routes/request.py`): só em passeio publicado, com data futura e recebendo pedidos. Só o dono e o admin veem os pedidos de uma data. Quando o guia aceita a última vaga, a data fica esgotada sozinha.
- **Página de perfil**: `POST /pages/profile`.
- **Cidades pela CidadesBR-API** (veja a seção própria mais abaixo):
  - `GET /cidades/busca?q=<texto>&uf=<UF>`: sugestões de cidade para o formulário do passeio
  - `GET /tour/perto?lat=<lat>&lon=<lon>`: passeios publicados, do mais perto para o mais longe
- **Banco versionado** em `supabase/migrations`, com seed de teste em `supabase/seed.sql`.
- **Modo local** sem token nenhum (`python run.py --local`).
- **Chaves fora do repositório**: ficam num arquivo privado no Google Drive (veja o passo 5).

---

## Como reproduzir a API em outro computador

## 1) Clonar o projeto
```bash
git clone https://github.com/ViajaAPP/viaja_flaskapp.git
cd viaja_flaskapp
git checkout staging
```

Quem já tinha o repositório clonado antes de 29/09/2026 precisa **apagar e clonar de novo**: o histórico foi reescrito para tirar chaves que estavam no README. Um push de um clone antigo traz as chaves de volta.

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

No modo local, as rotas de cidade usam a CidadesBR-API publicada, sem precisar de chave. Se ela estiver dormindo, a primeira busca pode levar perto de um minuto.

## 5) Rodar com o Supabase e o ngrok de verdade
As chaves de produção não ficam no repositório. Elas ficam no arquivo privado `viaja-backend.env`, no Google Drive da Erika, e o script `scripts/secrets.sh` baixa esse arquivo e escreve o `.env`. Não precisa de faturamento no Google Cloud.

### Como pegar as chaves
1. **Peça acesso à Erika.** Ela compartilha o `viaja-backend.env` com o seu email do Google. Quem já tem acesso: Sophia, Marcos e Giovanna.
2. **Instale o Google Cloud SDK** (`gcloud`) e entre com esse mesmo email, dando acesso ao Drive:
   ```bash
   gcloud auth login --enable-gdrive-access
   ```
   Se você já usa o `gcloud` com outra conta (do trabalho, por exemplo), crie uma configuração separada para o Viaja antes do login, e o script passa a usar ela sozinho:
   ```bash
   gcloud config configurations create viaja --no-activate
   CLOUDSDK_ACTIVE_CONFIG_NAME=viaja gcloud auth login --enable-gdrive-access
   ```
3. **Baixe as chaves e suba a API:**
   ```bash
   bash scripts/secrets.sh pull
   python run.py
   ```

O `pull` escreve o `.env` com:

| Variável | Para que serve |
| --- | --- |
| `SUPABASE_URL`, `SUPABASE_KEY` | acesso ao banco de produção |
| `AUTH_CRYPT_KEY` | assina o token de login do app |
| `NGROK_API_TOKEN`, `NGROK_WS_TOKEN` | abrem os túneis da API e do WebSocket |
| `FLASK_ENV` | modo do Flask |
| `SUPABASE_PROJECT_REF`, `SUPABASE_DB_PASSWORD` | usadas para aplicar migrations no banco de produção |
| `CIDADESBR_API_URL` | endereço da CidadesBR-API. Sem ela, o back usa `https://cidadesbr-api.onrender.com` |
| `CIDADESBR_ADMIN_API_KEY` | chave das rotas `/admin` da CidadesBR-API. O back não usa; serve para consultar o uso da API |
| `CONTAS_TESTE_SENHA` | senha das contas de teste na produção (veja abaixo). O back não usa |

O `.env` nunca vai para o git. Para voltar ao banco local depois, rode `bash scripts/secrets.sh local`.

### Contas de teste na produção
A produção tem as mesmas contas de teste do modo local: `guia@viaja.local`, `viajante@viaja.local` e `admin@viaja.local`. A senha **não** é `viaja123`: é a `CONTAS_TESTE_SENHA` que o `pull` escreve no `.env`. Para ver:
```bash
grep CONTAS_TESTE_SENHA .env
```

### Trocar ou acrescentar uma chave
Só quem tem permissão de edição no arquivo do Drive consegue:
- `bash scripts/secrets.sh set SUPABASE_KEY`: troca uma chave. O valor é colado no terminal e não aparece na tela.
- `bash scripts/secrets.sh push <arquivo>`: manda um `.env` inteiro.
- `bash scripts/secrets.sh gerar`: cria uma `AUTH_CRYPT_KEY` aleatória, se ela ainda não existir.

### Banco de produção
Mudanças de estrutura ficam em `supabase/migrations`:
- `20260929110000_schema_inicial.sql`: tabelas e funções que o código usa. Não muda nada que já exista no banco.
- `20260929120000_tour_management.sql`: cria `tour.published` e `tour_instance.registration`, renomeia `tour_request.last_update` para `last_updated` e acrescenta `ADMIN` ao papel do usuário. Já está aplicada em produção.

Para aplicar: `npx supabase link --project-ref <SUPABASE_PROJECT_REF>` e depois `npx supabase db push`.

### CidadesBR-API
É a API de municípios brasileiros feita para o Viaja: nome, UF, coordenadas e código do IBGE de cada cidade. Está publicada em `https://cidadesbr-api.onrender.com` (documentação em `/docs`).

- O back chama a API em `app/services/cidades_service.py`, com tempo limite de 60 segundos e cache de 24 horas por consulta. O cache segura o Render dormindo e o limite de 60 chamadas por minuto da API.
- `GET /tour/perto` pega a cidade e a UF do endereço de cada passeio publicado, busca as coordenadas da cidade e calcula a distância até o ponto recebido. Passeio sem endereço, ou com cidade que a API não conhece, fica de fora.
- Para ver o uso da API, com a `CIDADESBR_ADMIN_API_KEY` no `.env`:
  ```bash
  source .env && curl -H "X-Admin-Key: $CIDADESBR_ADMIN_API_KEY" "$CIDADESBR_API_URL/admin/usage"
  ```

### Problemas comuns
| Mensagem | O que fazer |
| --- | --- |
| `Sem login no Google. Rode: gcloud auth login --enable-gdrive-access` | Faça o login do passo 2. Se usa uma configuração separada, rode com `CLOUDSDK_ACTIVE_CONFIG_NAME=viaja` na frente. |
| `Não achei 'viaja-backend.env' no seu Drive` | O arquivo ainda não foi compartilhado com o email do login, ou o login foi feito com outro email. Confira com `gcloud auth list`. |
| `Não conheço '<NOME>'` | A variável não está na lista do `scripts/secrets.sh`. Use uma das opções que a mensagem mostra. |
| `O Supabase local não está rodando` | Abra o Docker e rode `npx supabase start`. |
| `bash: scripts/secrets.sh: No such file or directory` | Rode os comandos a partir da pasta `viaja_flaskapp`. No Windows, use o Git Bash. |
| A busca de cidade ou o "mais perto" demora na primeira vez | É a CidadesBR-API acordando no Render. As próximas respostas saem do cache. |

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
│  ├─ utils/auth.py        # login e permissões por papel
├─ scripts/secrets.sh      # chaves: pull, set, push, gerar e local
├─ supabase/
│  ├─ migrations/          # estrutura do banco
│  ├─ seed.sql             # dados de teste do banco local
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
