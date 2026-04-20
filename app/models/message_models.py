from pydantic import BaseModel
from datetime import datetime

class MessageCreateModel(BaseModel):
    content: str
    chat_id: int
    user_id: int

class MessageModel(MessageCreateModel):
    id: int
    sent_at: datetime