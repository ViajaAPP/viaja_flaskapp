from pydantic import BaseModel
from datetime import datetime

class MessageCreate(BaseModel):
    content: str
    chat_id: int
    user_id: int

class MessageModel(MessageCreate):
    id: int
    sent_at: datetime