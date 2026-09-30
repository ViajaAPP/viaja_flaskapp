from enum import Enum

class TourStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    DONE = "DONE"
    CANCELED = "CANCELLED"

class RegistrationStatus(str, Enum):
    OPEN = "OPEN"
    FULL = "FULL"
    CLOSED = "CLOSED"

class RequestStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DENIED = "DENIED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    
class UserRole(str, Enum):
    TOURIST = "TOURIST"
    GUIDE = "GUIDE"
    EVENT_PROMOTER = "EVENT_PROMOTER"
    ADMIN = "ADMIN"
    
class UF(str, Enum):
    AC = "AC"
    AL = "AL"
    AP = "AP"
    AM = "AM"
    BA = "BA"
    CE = "CE"
    DF = "DF"
    ES = "ES"
    GO = "GO"
    MA = "MA"
    MT = "MT"
    MS = "MS"
    MG = "MG"
    PA = "PA"
    PB = "PB"
    PR = "PR"
    PE = "PE"
    PI = "PI"
    RJ = "RJ"
    RN = "RN"
    RS = "RS"
    RO = "RO"
    RR = "RR"
    SC = "SC"
    SP = "SP"
    SE = "SE"
    TO = "TO"