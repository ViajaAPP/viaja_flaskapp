from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from .enums import TourStatus

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
    
class TourInstanceCreateModel(BaseModel):
    tour_id: int
    start_time: datetime
    max_capacity: int
    status: TourStatus = TourStatus.SCHEDULED

class TourInstanceModel(TourInstanceCreateModel):
    id: int
    created_at: datetime