from typing import Optional, List
from pydantic import BaseModel, ConfigDict

# Room Schemas
class RoomResponse(BaseModel):
    id: int
    room_number: str
    room_type: str
    price_per_night: float
    status: str

    model_config = ConfigDict(from_attributes=True)


# Guest Schemas
class GuestCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None

class GuestResponse(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Booking Schemas
class BookingCreate(BaseModel):
    guest_id: Optional[int] = None
    guest_name: Optional[str] = None
    room_id: Optional[int] = None
    room_number: Optional[str] = None
    check_in: str
    check_out: str
    guest_email: Optional[str] = None
    guest_phone: Optional[str] = None

class BookingResponse(BaseModel):
    id: int
    guest_id: int
    guest_name: Optional[str] = None
    room_id: int
    room_number: Optional[str] = None
    room_type: Optional[str] = None
    check_in: str
    check_out: str
    status: str

    model_config = ConfigDict(from_attributes=True)


# Agent Schemas
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    tools_called: Optional[List[str]] = None
