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

O Viajá liga quem quer conhecer um lugar a quem mora lá e sabe mostrar. Esta é a API: contas, passeios, reservas, eventos, chat e avaliações. O app fica no [viaja-front](https://github.com/ViajaAPP/viaja-front).

A versão que está valendo fica na branch `staging`.

---

## O que você precisa ter

| Programa | Para quê |
| --- | --- |
| [Python](https://www.python.org/downloads/) 3.9 ou mais novo | rodar a API. A gente usa a 3.14 |
| [Node.js](https://nodejs.org/) 20 ou mais novo | o `npx` que sobe o banco local |
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) aberto | é onde o banco local roda |
| [Git](https://git-scm.com/downloads) | no Windows ele traz o **Git Bash**, que é o terminal usado aqui |

> No Windows, faça tudo no **Git Bash**, do começo ao fim. O PowerShell não roda os scripts `.sh` e, se você trocar de terminal no meio, o ambiente do Python fica para trás.

---

## Rodar na sua máquina

São seis passos, sem chave nenhuma. O banco sobe no seu computador, já com tabelas e dados de teste.

### 1. Clone o projeto

```bash
git clone https://github.com/ViajaAPP/viaja_flaskapp.git
cd viaja_flaskapp
git checkout staging
```

### 2. Crie o ambiente do Python

No Git Bash (Windows):

```bash
python -m venv .venv
source .venv/Scripts/activate
```

No Linux ou macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

O nome `(.venv)` aparece no começo da linha. Toda vez que abrir um terminal novo, rode o `source` de novo.

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Suba o banco local

Com o Docker aberto:

```bash
npx -y supabase start
```

Na primeira vez ele baixa as imagens e demora alguns minutos. Quando termina, mostra uma lista de endereços.

### 5. Crie o arquivo de ambiente local

```bash
bash scripts/secrets.sh local
```

Ele escreve o `.env` apontando para o banco que acabou de subir.

### 6. Suba a API

```bash
python run.py --local
```

### Deu certo?

Abra [http://localhost:5000/docs](http://localhost:5000/docs). Se aparecer a lista de rotas, está tudo rodando.

| O quê | Onde |
| --- | --- |
| API | http://localhost:5000 |
| Documentação das rotas | http://localhost:5000/docs |
| Chat | `ws://localhost:8765` e `ws://localhost:5000/ws` |
| Painel do banco | http://localhost:54323 |

Agora suba o front seguindo o [README do viaja-front](https://github.com/ViajaAPP/viaja-front/tree/staging#readme). Ele já procura a API em `localhost:5000`.

---

## Local ou produção

O que decide o banco é o `.env`, e quem escreve o `.env` é o `secrets.sh`. Para trocar de modo, rode o `secrets.sh` do modo que você quer e suba a API de novo.

| Modo | Comandos | Banco |
| --- | --- | --- |
| Local | `bash scripts/secrets.sh local` e `python run.py --local` | Supabase na sua máquina, com dados de teste |
| Produção | `bash scripts/secrets.sh pull` e `python run.py` | Supabase de produção, com dados reais |

O `.env` fica fora do git. Antes de subir a API, confira em qual modo ele está, para não gravar na produção achando que está no local.

### Contas de teste

No modo local, a senha de todas é `viaja123`:

| E-mail | Quem é |
| --- | --- |
| `guia@viaja.local` | a Fabi, guia com passeios publicados |
| `viajante@viaja.local` | o Tito, que reserva passeios |
| `produtor@viaja.local` | a Lia, que cadastra eventos |
| `admin@viaja.local` | quem modera e aprova os eventos |

Bagunçou os dados? `npx -y supabase db reset` volta tudo ao começo.

### Usar a produção

As chaves de produção não ficam no repositório. Elas estão no arquivo `viaja-backend.env`, no Google Drive da Erika.

1. Peça para a Erika compartilhar o arquivo com o seu e-mail do Google.
2. Instale o [gcloud](https://cloud.google.com/sdk/docs/install) e entre com esse e-mail:
   ```bash
   gcloud auth login --enable-gdrive-access
   ```
   Se você já usa o gcloud com outra conta, crie uma configuração só para o Viajá antes. O script usa ela sozinho:
   ```bash
   gcloud config configurations create viaja --no-activate
   CLOUDSDK_ACTIVE_CONFIG_NAME=viaja gcloud auth login --enable-gdrive-access
   ```
3. Baixe as chaves e suba a API:
   ```bash
   bash scripts/secrets.sh pull
   python run.py
   ```

Na produção, as contas de teste existem, mas a senha é a `CONTAS_TESTE_SENHA` que o `pull` colocou no `.env`.

---

## Quando algo dá errado

| O que aparece | O que fazer |
| --- | --- |
| `bash: scripts/secrets.sh: No such file or directory` | Você está fora da pasta `viaja_flaskapp`, ou no PowerShell. Use o Git Bash. |
| `ModuleNotFoundError` ao rodar o `run.py` | O ambiente do Python não está ativo. Rode o `source` do passo 2. |
| `O Supabase local não está rodando` | Abra o Docker e rode `npx -y supabase start`. |
| `Cannot connect to the Docker daemon` | O Docker Desktop está fechado. Abra e espere ele terminar de iniciar. |
| `Sem login no Google` | Faça o login do passo 2 de "Usar a produção". |
| `Não achei 'viaja-backend.env' no seu Drive` | O arquivo ainda não foi compartilhado com você, ou você entrou com outro e-mail. Confira com `gcloud auth list`. |
| A busca de cidade demora na primeira vez | É a CidadesBR-API acordando no Render. Depois as respostas saem do cache. |

---

## O que a API faz

- **Contas e papéis.** Quem se cadastra entra como viajante, guia ou produtor de eventos. O admin não aparece no cadastro. As regras de quem pode o quê ficam em `app/utils/auth.py`.
- **Passeios.** O guia cria o passeio com fotos, endereço e datas, e escolhe as vagas e o mínimo de pessoas para sair.
- **Pedidos e reservas.** O viajante pede uma vaga e o guia aceita ou recusa. Sem resposta em 24 horas, o pedido vence sozinho. Com a reserva instantânea ligada, a vaga já sai confirmada.
- **Busca e recomendação.** Acha passeio e destino do Brasil inteiro desde a primeira letra, com filtros de preço, data e distância. O "Para você" aprende com o que a pessoa procura e reserva.
- **Eventos.** Só o produtor cria, e o evento só aparece depois que um admin aprova.
- **Chat.** Cada data de passeio e cada evento tem o seu grupo, com localização ao vivo perto da hora.
- **Avaliações e avisos.** Nota e comentário depois do passeio, e aviso quando um pedido é aceito, recusado ou vence.

## Serviços que a API usa

| Serviço | Para quê |
| --- | --- |
| [Supabase](https://supabase.com/) | banco de dados e login |
| [CidadesBR-API](https://github.com/zerikazz/CidadesBR-API) | municípios do Brasil com coordenadas |
| [Photon](https://photon.komoot.io/) | busca de endereço, sem chave |
| [BrasilAPI](https://brasilapi.com.br/) | conferir o CNPJ do produtor de eventos |
| Redis | cache. Sem ele, o cache fica na memória |

## Variáveis de ambiente

O `secrets.sh` escreve o `.env` sozinho. Esta tabela é só para saber o que cada uma faz.

| Variável | Para quê |
| --- | --- |
| `SUPABASE_URL`, `SUPABASE_KEY` | entrar no banco |
| `AUTH_CRYPT_KEY` | assinar o token de login |
| `DADOS_CRYPT_KEY` | cifrar os dados pessoais guardados no banco |
| `PUBLIC_URL_WS` | onde o app encontra o chat |
| `CIDADESBR_API_URL` | endereço da CidadesBR-API |
| `APP_URL` | endereço do front, usado no e-mail de trocar a senha |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | de onde sai o e-mail |
| `REDIS_URL` | cache no Redis |
| `CORS_ORIGINS` | quem pode chamar a API |

## Como o projeto está organizado

```text
viaja_flaskapp/
├── app/
│   ├── models/        entidades do banco
│   ├── routes/        rotas da API
│   ├── services/      regras de negócio
│   └── utils/auth.py  login e quem pode o quê
├── scripts/
│   ├── secrets.sh     monta o .env
│   ├── semear_passeios.py
│   └── semear_eventos.py
├── supabase/
│   ├── migrations/    estrutura do banco
│   └── seed.sql       dados de teste do modo local
├── config.py          configurações lidas do ambiente
├── run.py             sobe a API e o chat
└── render.yaml        como publicar no Render
```

Toda mudança na estrutura do banco vira um arquivo em `supabase/migrations`. Para levar as que faltam para a produção:

```bash
npx -y supabase link --project-ref <SUPABASE_PROJECT_REF>
npx -y supabase db push
```

## Grupo

Daniel Ferreira Pinheiro da Silva, Érika Maria de Sousa, Giovanna Nassar Lara Santos, Marcos Rebouças Duarte da Silva e Sophia Verardo de Araújo.
