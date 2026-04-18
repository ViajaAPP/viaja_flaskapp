from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class TourCreateModel(BaseModel):
    created_by_id: int
    title: str
    description: Optional[str] = None
    price: float
    estimated_duration_minutes: int
    meeting_point: str
    
class TourModel(TourCreateModel):
    id: int
    created_at: datetime