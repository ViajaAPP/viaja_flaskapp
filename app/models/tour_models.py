from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from .enums import TourStatus, RegistrationStatus

class TourCreateModel(BaseModel):
    created_by_id: int
    title: str
    description: Optional[str] = None
    price: float
    estimated_duration_minutes: int
    meeting_point: str
    photo: str
    address_id: int
    published: bool = False

class TourModel(TourCreateModel):
    id: int
    created_at: datetime

class TourUpdateModel(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    estimated_duration_minutes: Optional[int] = None
    meeting_point: Optional[str] = None
    photo: Optional[str] = None
    address_id: Optional[int] = None

class TourInstanceCreateModel(BaseModel):
    tour_id: int
    start_time: datetime
    max_capacity: int
    status: TourStatus = TourStatus.SCHEDULED
    registration: RegistrationStatus = RegistrationStatus.OPEN

class TourInstanceModel(TourInstanceCreateModel):
    id: int
    created_at: datetime

class TourInstanceUpdateModel(BaseModel):
    start_time: Optional[datetime] = None
    max_capacity: Optional[int] = None
    status: Optional[TourStatus] = None
    registration: Optional[RegistrationStatus] = None
