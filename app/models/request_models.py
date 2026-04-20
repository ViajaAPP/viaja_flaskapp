from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from .enums import RequestStatus

class TourRequestCreateModel(BaseModel):
    tour_instance_id: int
    requester_id: int
    status: RequestStatus = RequestStatus.PENDING
    message: Optional[str] = None
    
class TourRequestModel(TourRequestCreateModel):
    id: int
    created_at: datetime
    last_updated: Optional[datetime] = None