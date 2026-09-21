from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Booking, Room, Guest
from app.schemas import BookingCreate, BookingResponse
from app.tools import create_booking, cancel_booking

router = APIRouter(prefix="/bookings", tags=["Bookings"])

@router.get("", response_model=List[BookingResponse])
def get_bookings(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Booking)
    if status:
        query = query.filter(Booking.status.ilike(status.strip()))
    bookings = query.order_by(Booking.id.desc()).all()
    return [
        BookingResponse(
            id=b.id,
            guest_id=b.guest_id,
            guest_name=b.guest.name if b.guest else None,
            room_id=b.room_id,
            room_number=b.room.room_number if b.room else None,
            room_type=b.room.room_type if b.room else None,
            check_in=b.check_in,
            check_out=b.check_out,
            status=b.status
        )
        for b in bookings
    ]

@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_new_booking(payload: BookingCreate, db: Session = Depends(get_db)):
    # Determine room number
    room_number = payload.room_number
    if not room_number and payload.room_id:
        room = db.query(Room).filter(Room.id == payload.room_id).first()
        if room:
            room_number = room.room_number

    if not room_number:
        raise HTTPException(status_code=400, detail="room_number or valid room_id is required")

    # Determine guest name
    guest_name = payload.guest_name
    if not guest_name and payload.guest_id:
        guest = db.query(Guest).filter(Guest.id == payload.guest_id).first()
        if guest:
            guest_name = guest.name

    if not guest_name:
        raise HTTPException(status_code=400, detail="guest_name or valid guest_id is required")

    result = create_booking(
        db=db,
        guest_name=guest_name,
        room_number=room_number,
        check_in=payload.check_in,
        check_out=payload.check_out,
        guest_email=payload.guest_email,
        guest_phone=payload.guest_phone
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    booking = db.query(Booking).filter(Booking.id == result["booking_id"]).first()
    return BookingResponse(
        id=booking.id,
        guest_id=booking.guest_id,
        guest_name=booking.guest.name if booking.guest else None,
        room_id=booking.room_id,
        room_number=booking.room.room_number if booking.room else None,
        room_type=booking.room.room_type if booking.room else None,
        check_in=booking.check_in,
        check_out=booking.check_out,
        status=booking.status
    )

@router.delete("/{booking_id}")
def delete_booking(booking_id: int, db: Session = Depends(get_db)):
    result = cancel_booking(db=db, booking_id=booking_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result
