import queue
import threading
from app.services.supabase_service import supabase
from app.models.message_models import MessageCreate, MessageModel

# A fila é instanciada aqui para ser um Singleton no módulo
msg_queue = queue.Queue()

def process_messages():
    """Worker que processa a fila infinitamente"""
    while True:
        dados = msg_queue.get()
        if dados is None: # Sinal de parada
            break

        try:
            new_msg = MessageCreate(**dados)
            
            # Insere no Supabase
            supabase.table("messages").insert(new_msg.model_dump()).execute()
            print(f"Mensagem do chat {new_msg.chat_id} processada com sucesso!")

        except Exception as e:
            print(f"Erro no Worker de Mensagens: {e}")
        finally:
            msg_queue.task_done()

def init_message_worker():
    """Inicia a thread do worker"""
    worker = threading.Thread(target=process_messages, daemon=True)
    worker.start()

def enqueue_message(content: str, chat_id: int, user_id: int):
    """Função que as rotas chamarão para enfileirar mensagens"""
    msg_queue.put({
        "content": content,
        "chat_id": chat_id,
        "user_id": user_id
    })