# Viajá FlaskAPP

Instruções mínimas para preparar e executar a aplicação Flask neste diretório.

## Pré-requisitos
- Python 3.8+ instalado
- pip disponível
- (Opcional) git

## Instalação (ambiente virtual recomendado)

Linux / macOS:
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt  # se existir
```

Windows (CMD):
```cmd
python -m venv venv
venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

Windows (PowerShell):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

## Variáveis de ambiente
Defina a variável que aponta para a aplicação Flask. Substitua `app.py` ou `viaja:app` conforme o ponto de entrada do seu projeto.

Linux / macOS:
```bash
export FLASK_APP=app.py        # ou export FLASK_APP=viaja:create_app
export FLASK_ENV=development  # opcional, modo dev
```

Windows (CMD):
```cmd
set FLASK_APP=app.py
set FLASK_ENV=development
```

Windows (PowerShell):
```powershell
$env:FLASK_APP = "app.py"
$env:FLASK_ENV = "development"
```

## Executar em desenvolvimento
```bash
flask run --host=0.0.0.0 --port=5000
```
ou (caso use `python` diretamente)
```bash
python -m flask run
```

## Executar em produção (exemplo com gunicorn, Linux)
Instale gunicorn:
```bash
pip install gunicorn
```
Execute:
```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app   # ajuste "app:app" conforme seu módulo/objeto
```

## Observações
- Ajuste os nomes de arquivos e o valor de FLASK_APP conforme a estrutura do projeto (ex.: `viaja:app` ou factory `viaja:create_app()`).
- Se o repositório tiver um `Procfile`, `dockerfile` ou instruções adicionais, siga-os para deploy em plataformas específicas.
- Para problemas com dependências, recrie o virtualenv e reinstale.

Se precisar, posso gerar um exemplo de `requirements.txt` ou detectar automaticamente o ponto de entrada se você listar os arquivos do diretório.
