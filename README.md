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
- Git. No Windows, rode os scripts `.sh` pelo Git Bash.
- Node.js, porque o banco local sobe com o `npx supabase`.
- Docker aberto, que é onde o banco local roda.
- Google Cloud SDK (`gcloud`), só se você for usar as chaves de produção: https://cloud.google.com/sdk/docs/install

---

## O que a API faz hoje
A versão que está funcionando fica na branch `staging`. É ela que você deve usar.

- **Contas e papéis.** Quem se cadastra entra como viajante (`TOURIST`), guia (`GUIDE`) ou produtor de eventos (`EVENT_PROMOTER`). O `ADMIN` não aparece no cadastro. As regras de quem pode o quê ficam em `app/utils/auth.py`.
- **Passeios.** O guia cria o passeio, coloca fotos, endereço e datas, e escolhe quantas vagas tem e o mínimo de pessoas para sair. Rascunho só aparece para o próprio guia e para o admin.
- **Pedidos e reservas.** O viajante pede uma vaga e o guia aceita ou recusa. Se o guia não responder em 24 horas, o pedido vence sozinho. O guia também pode ligar a reserva instantânea, e aí a vaga já sai confirmada. Quando a última vaga é preenchida, a data fica lotada.
- **Busca e recomendação.** A busca acha passeio e destino do Brasil inteiro desde a primeira letra. Dá para filtrar só os grátis ou por data, e ordenar por nota, preço ou distância. O "Para você" monta a ordem pelo que a pessoa já procurou e reservou (`app/services/busca_service.py`).
- **Avaliações.** Quem foi ao passeio dá nota e escreve como foi. O passeio mostra a média e quanto tempo o guia costuma levar para responder.
- **Avisos.** O app avisa quando um pedido é aceito, recusado ou vence, e quando um evento muda.
- **Eventos.** Só quem se cadastrou como produtor de eventos cria evento, e ele só aparece depois que um admin aprova. Se o admin recusar, precisa dizer o motivo.
- **Endereço e mapa.** A busca de endereço usa o Photon, que é gratuito e não precisa de chave. As cidades vêm da CidadesBR-API (veja mais abaixo).
- **Cache.** As respostas que mais se repetem ficam guardadas por alguns minutos, no Redis quando ele existe e na memória quando não existe. Qualquer mudança em passeio, pedido, favorito ou evento limpa o que estava guardado.
- **E-mail.** Serve para recuperar a senha. Sai por uma conta do Gmail com senha de app.

As rotas estão todas documentadas em `/docs`, com a API rodando.

---

## Como reproduzir a API em outro computador

## 1) Clonar o projeto
```bash
git clone https://github.com/ViajaAPP/viaja_flaskapp.git
cd viaja_flaskapp
git checkout staging
```

Se você clonou antes de 29/09/2026, apague a pasta e clone de novo. Reescrevemos o histórico para tirar umas chaves que tinham ido parar no README, e um push vindo de um clone antigo traz essas chaves de volta.

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

## 4) Rodar tudo na sua máquina, sem chave nenhuma
Esse é o jeito mais fácil de começar. Com o Docker aberto, o Supabase sobe na sua máquina já com as tabelas e uns dados de teste:
```bash
npx supabase start
bash scripts/secrets.sh local
python run.py --local
```

Pronto, aí você tem:
- a API em `http://localhost:5000`, com a documentação em `/docs`;
- o WebSocket do chat em `ws://localhost:8765`;
- o painel do banco em `http://localhost:54323`.

Para entrar no app, use uma das contas de teste. A senha de todas é `viaja123`:
- `guia@viaja.local`: a Fabi, guia com passeios publicados;
- `viajante@viaja.local`: o Tito, que reserva passeios;
- `admin@viaja.local`: quem modera e aprova os eventos;
- `produtor@viaja.local`: a Lia, que cadastra eventos.

Se você bagunçar os dados e quiser voltar ao começo, rode `npx supabase db reset`.

No front, o `npm start` já procura a API em `http://localhost:5000`, então não precisa configurar nada.

Mesmo rodando local, a busca de cidade usa a CidadesBR-API que está no ar. Se ela estiver dormindo, a primeira busca pode levar quase um minuto.

### Testar o e-mail sem mandar e-mail de verdade
O Mailpit pega os e-mails que a API manda e mostra numa página:
```bash
docker run -d --name viaja-mailpit -p 1025:1025 -p 8025:8025 axllent/mailpit
```
Acrescente `SMTP_HOST=localhost`, `SMTP_PORT=1025` e `SMTP_FROM=teste@viaja.local` no `.env` e reinicie a API. Os e-mails aparecem em `http://localhost:8025`. Sem essas variáveis, a API simplesmente não manda e-mail.

## 5) Rodar com o banco de produção
As chaves de produção não ficam no repositório. Elas ficam no arquivo `viaja-backend.env`, guardado no Google Drive da Erika, e o `scripts/secrets.sh` baixa esse arquivo e monta o seu `.env`. Não precisa de faturamento no Google Cloud.

### Como pegar as chaves
1. **Peça acesso para a Erika.** Ela compartilha o `viaja-backend.env` com o seu e-mail do Google. A Sophia, o Marcos e a Giovanna já têm acesso.
2. **Instale o `gcloud` e entre com esse mesmo e-mail**, liberando o acesso ao Drive:
   ```bash
   gcloud auth login --enable-gdrive-access
   ```
   Se você já usa o `gcloud` com outra conta, do trabalho por exemplo, crie uma configuração só para o Viajá antes de entrar. O script usa ela sozinho:
   ```bash
   gcloud config configurations create viaja --no-activate
   CLOUDSDK_ACTIVE_CONFIG_NAME=viaja gcloud auth login --enable-gdrive-access
   ```
3. **Baixe as chaves e suba a API:**
   ```bash
   bash scripts/secrets.sh pull
   python run.py
   ```

Depois do `pull`, o seu `.env` fica com estas variáveis:

| Variável | Para que serve |
| --- | --- |
| `SUPABASE_URL`, `SUPABASE_KEY` | entrar no banco de produção |
| `AUTH_CRYPT_KEY` | assinar o token de login do app |
| `NGROK_API_TOKEN`, `NGROK_WS_TOKEN` | abrir os túneis da API e do WebSocket |
| `FLASK_ENV` | modo do Flask |
| `SUPABASE_PROJECT_REF`, `SUPABASE_DB_PASSWORD` | aplicar migrations no banco de produção |
| `CIDADESBR_API_URL` | endereço da CidadesBR-API. Se faltar, o back usa `https://cidadesbr-api.onrender.com` |
| `CIDADESBR_ADMIN_API_KEY` | ver quanto a CidadesBR-API está sendo usada. O back não usa |
| `CONTAS_TESTE_SENHA` | senha das contas de teste na produção. O back também não usa |

Algumas variáveis têm um valor padrão e só precisam ir no `.env` se você quiser trocar:

| Variável | Para que serve |
| --- | --- |
| `APP_URL` | endereço do front, usado no link do e-mail de trocar a senha. Padrão: `http://localhost:4200` |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | de onde sai o e-mail. Padrão: Gmail na porta 587 |
| `PHOTON_URL` | busca de endereço. Padrão: `https://photon.komoot.io` |
| `REDIS_URL` | cache no Redis. Sem ela, o cache fica na memória da API |
| `CORS_ORIGINS`, `PUBLIC_URL_WS` | quem pode chamar a API e onde fica o WebSocket |

O `.env` nunca vai para o git. Para voltar ao banco local, rode `bash scripts/secrets.sh local`.

### Contas de teste na produção
A produção tem as mesmas contas de teste do modo local, inclusive a da Lia, mas a senha **não** é `viaja123`. É a `CONTAS_TESTE_SENHA` que o `pull` colocou no seu `.env`:
```bash
grep CONTAS_TESTE_SENHA .env
```

### Trocar ou acrescentar uma chave
Só quem pode editar o arquivo no Drive consegue fazer isso:
- `bash scripts/secrets.sh set SUPABASE_KEY` troca uma chave. Você cola o valor no terminal e ele não aparece na tela.
- `bash scripts/secrets.sh push <arquivo>` manda um `.env` inteiro.
- `bash scripts/secrets.sh gerar` cria uma `AUTH_CRYPT_KEY` aleatória, se ainda não tiver uma.

### Banco de produção
Toda mudança na estrutura do banco vira um arquivo em `supabase/migrations`, com a data no nome. A primeira, `schema_inicial`, só descreve o banco que já existia. Depois dela vieram as fotos, os favoritos, a troca de senha, a localização dos endereços, as avaliações, os avisos, a reserva instantânea com mínimo de pessoas e os eventos. Todas já estão em produção.

Para aplicar as que faltam:
```bash
npx supabase link --project-ref <SUPABASE_PROJECT_REF>
npx supabase db push
```

### CidadesBR-API
É uma API com todos os municípios do Brasil, feita para o Viajá: nome, UF, coordenadas e código do IBGE. Ela está no ar em `https://cidadesbr-api.onrender.com`, com a documentação em `/docs`.

- O back chama a API em `app/services/cidades_service.py`. Ele espera até 60 segundos e guarda cada resposta por 24 horas. Assim, o Render dormindo e o limite de 60 chamadas por minuto quase não aparecem para quem usa o app.
- Para ver quanto a API está sendo usada, com a `CIDADESBR_ADMIN_API_KEY` no `.env`:
  ```bash
  source .env && curl -H "X-Admin-Key: $CIDADESBR_ADMIN_API_KEY" "$CIDADESBR_API_URL/admin/usage"
  ```

### Publicar no Render
O `render.yaml` já deixa tudo pronto para publicar de graça no Render: a API com o gunicorn e um Redis para o cache. Ainda não publicamos, porque falta registrar o domínio `viaja-app.com.br`. As chaves entram pelo painel do Render, nunca pelo arquivo.

### Quando algo dá errado
| Mensagem | O que fazer |
| --- | --- |
| `Sem login no Google. Rode: gcloud auth login --enable-gdrive-access` | Faça o login do passo 2. Se você criou a configuração `viaja`, coloque `CLOUDSDK_ACTIVE_CONFIG_NAME=viaja` na frente do comando. |
| `Não achei 'viaja-backend.env' no seu Drive` | O arquivo ainda não foi compartilhado com você, ou você entrou com outro e-mail. Confira com `gcloud auth list`. |
| `Não conheço '<NOME>'` | Essa variável não está na lista do `scripts/secrets.sh`. A própria mensagem mostra as que existem. |
| `O Supabase local não está rodando` | Abra o Docker e rode `npx supabase start`. |
| `bash: scripts/secrets.sh: No such file or directory` | Você está fora da pasta `viaja_flaskapp`. No Windows, use o Git Bash. |
| A busca de cidade demora na primeira vez | É a CidadesBR-API acordando no Render. Depois disso as respostas saem do cache. |

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
│  ├─ utils/auth.py        # login e quem pode o quê
├─ scripts/
│  ├─ secrets.sh           # baixa e troca as chaves
│  ├─ semear_passeios.py   # coloca os passeios de exemplo no banco
├─ supabase/
│  ├─ migrations/          # estrutura do banco
│  ├─ dados/passeios.json  # os passeios de exemplo
│  ├─ seed.sql             # dados de teste do banco local
├─ render.yaml             # como publicar no Render
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
