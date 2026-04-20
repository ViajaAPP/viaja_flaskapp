from enum import Enum

class TourStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    DONE = "DONE"
    CANCELED = "CANCELED"

class RequestStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DENIED = "DENIED"
    
class UserRole(str, Enum):
    TOURIST = "TOURIST"
    GUIDE = "GUIDE"
    EVENT_PROMOTER = "EVENT_PROMOTER"