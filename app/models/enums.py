from enum import Enum

class TourStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    DONE = "DONE"
    CANCELED = "CANCELED"

class RequestStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DENIED = "DENIED"