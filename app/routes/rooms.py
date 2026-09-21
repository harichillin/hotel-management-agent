from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Room
from app.schemas import RoomResponse

router = APIRouter(prefix="/rooms", tags=["Rooms"])

@router.get("", response_model=List[RoomResponse])
def get_rooms(
    room_type: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Room)
    if room_type:
        query = query.filter(Room.room_type.ilike(f"%{room_type.strip()}%"))
    if status:
        query = query.filter(Room.status.ilike(status.strip()))
    return query.order_by(Room.room_number).all()
