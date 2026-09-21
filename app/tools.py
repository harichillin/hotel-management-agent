import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.models import Room, Guest, Booking

def check_room_availability(
    db: Session,
    room_type: Optional[str] = None,
    check_in: Optional[str] = None,
    check_out: Optional[str] = None
) -> Dict[str, Any]:
    """Check whether rooms are available, optionally filtering by room type and date range."""
    query = db.query(Room)
    if room_type:
        query = query.filter(Room.room_type.ilike(f"%{room_type.strip()}%"))

    all_matching_rooms = query.all()

    # If dates are provided, find rooms with overlapping confirmed bookings
    unavailable_room_ids = set()
    if check_in and check_out:
        overlapping_bookings = db.query(Booking).filter(
            Booking.status == "confirmed",
            Booking.check_in < check_out,
            Booking.check_out > check_in
        ).all()
        unavailable_room_ids = {b.room_id for b in overlapping_bookings}

    available_rooms = []
    for r in all_matching_rooms:
        if r.id in unavailable_room_ids:
            continue
        # Also respect room.status if dates were not specified
        if not check_in and not check_out and r.status.lower() != "available":
            continue
        available_rooms.append({
            "id": r.id,
            "room_number": r.room_number,
            "room_type": r.room_type,
            "price_per_night": r.price_per_night,
            "status": r.status
        })

    return {
        "success": True,
        "available_count": len(available_rooms),
        "rooms": available_rooms,
        "filter": {"room_type": room_type, "check_in": check_in, "check_out": check_out}
    }


def create_booking(
    db: Session,
    guest_name: str,
    room_number: str,
    check_in: str,
    check_out: str,
    guest_email: Optional[str] = None,
    guest_phone: Optional[str] = None
) -> Dict[str, Any]:
    """Create a booking for an existing or new guest."""
    room = db.query(Room).filter(Room.room_number == str(room_number).strip()).first()
    if not room:
        return {"success": False, "error": f"Room '{room_number}' not found."}

    # Check for conflict with existing confirmed bookings
    conflict = db.query(Booking).filter(
        Booking.room_id == room.id,
        Booking.status == "confirmed",
        Booking.check_in < check_out,
        Booking.check_out > check_in
    ).first()
    if conflict:
        return {
            "success": False,
            "error": f"Room {room_number} is already booked from {conflict.check_in} to {conflict.check_out}."
        }

    # Find or create guest
    guest = db.query(Guest).filter(Guest.name.ilike(guest_name.strip())).first()
    if not guest:
        guest = Guest(
            name=guest_name.strip(),
            email=guest_email or f"{guest_name.lower().replace(' ', '.')}@example.com",
            phone=guest_phone or "+1-555-0199"
        )
        db.add(guest)
        db.flush()

    new_booking = Booking(
        guest_id=guest.id,
        room_id=room.id,
        check_in=check_in,
        check_out=check_out,
        status="confirmed"
    )
    db.add(new_booking)

    # Check if booking is active today
    today = datetime.date.today().isoformat()
    if check_in <= today < check_out:
        room.status = "occupied"

    db.commit()
    db.refresh(new_booking)

    return {
        "success": True,
        "booking_id": new_booking.id,
        "guest_name": guest.name,
        "room_number": room.room_number,
        "room_type": room.room_type,
        "check_in": new_booking.check_in,
        "check_out": new_booking.check_out,
        "status": new_booking.status,
        "price_per_night": room.price_per_night
    }


def get_bookings(
    db: Session,
    status: Optional[str] = None,
    today_only: Optional[bool] = False,
    guest_name: Optional[str] = None
) -> Dict[str, Any]:
    """Return existing bookings, with optional filters."""
    query = db.query(Booking)

    if status:
        query = query.filter(Booking.status.ilike(status.strip()))

    if guest_name:
        query = query.join(Guest).filter(Guest.name.ilike(f"%{guest_name.strip()}%"))

    if today_only:
        today = datetime.date.today().isoformat()
        # Booking is active today if check_in <= today <= check_out or check_in == today
        query = query.filter(Booking.check_in <= today, Booking.check_out >= today)

    bookings = query.order_by(Booking.id.desc()).all()
    return {
        "success": True,
        "total": len(bookings),
        "bookings": [b.to_dict() for b in bookings]
    }


def cancel_booking(db: Session, booking_id: int) -> Dict[str, Any]:
    """Cancel an existing booking by its ID."""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        return {"success": False, "error": f"Booking ID #{booking_id} not found."}

    if booking.status == "cancelled":
        return {"success": False, "error": f"Booking ID #{booking_id} is already cancelled."}

    booking.status = "cancelled"

    # If the room has no other active confirmed bookings for today, reset room status to available
    today = datetime.date.today().isoformat()
    active_now = db.query(Booking).filter(
        Booking.room_id == booking.room_id,
        Booking.status == "confirmed",
        Booking.check_in <= today,
        Booking.check_out >= today
    ).count()

    if active_now == 0 and booking.room:
        booking.room.status = "available"

    db.commit()

    return {
        "success": True,
        "booking_id": booking_id,
        "message": f"Booking #{booking_id} for Room {booking.room.room_number if booking.room else 'Unknown'} has been cancelled successfully."
    }


def get_guests(db: Session, name: Optional[str] = None) -> Dict[str, Any]:
    """Return guest information, optionally searching by name."""
    query = db.query(Guest)
    if name:
        query = query.filter(Guest.name.ilike(f"%{name.strip()}%"))

    guests = query.all()
    return {
        "success": True,
        "total": len(guests),
        "guests": [g.to_dict() for g in guests]
    }


def get_rooms(
    db: Session,
    room_type: Optional[str] = None,
    status: Optional[str] = None
) -> Dict[str, Any]:
    """Return room information and status."""
    query = db.query(Room)
    if room_type:
        query = query.filter(Room.room_type.ilike(f"%{room_type.strip()}%"))
    if status:
        query = query.filter(Room.status.ilike(status.strip()))

    rooms = query.order_by(Room.room_number).all()
    return {
        "success": True,
        "total": len(rooms),
        "rooms": [r.to_dict() for r in rooms]
    }


# OpenAI Function Calling Tools Specification
HOTEL_TOOLS_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "check_room_availability",
            "description": "Check whether hotel rooms are available. Allows filtering by room type (e.g. Single, Double, Deluxe) and optional check-in/check-out dates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "room_type": {
                        "type": "string",
                        "description": "The type of room to filter by, e.g., 'Single', 'Double', or 'Deluxe'."
                    },
                    "check_in": {
                        "type": "string",
                        "description": "Check-in date in YYYY-MM-DD format."
                    },
                    "check_out": {
                        "type": "string",
                        "description": "Check-out date in YYYY-MM-DD format."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_booking",
            "description": "Create a new booking for a guest for a specific room and date range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "guest_name": {
                        "type": "string",
                        "description": "Full name of the guest."
                    },
                    "room_number": {
                        "type": "string",
                        "description": "The room number to book, e.g., '101', '201', '301'."
                    },
                    "check_in": {
                        "type": "string",
                        "description": "Check-in date in YYYY-MM-DD format. Default to today if not provided."
                    },
                    "check_out": {
                        "type": "string",
                        "description": "Check-out date in YYYY-MM-DD format. Default to tomorrow if not provided."
                    },
                    "guest_email": {
                        "type": "string",
                        "description": "Guest's email address (optional)."
                    },
                    "guest_phone": {
                        "type": "string",
                        "description": "Guest's phone number (optional)."
                    }
                },
                "required": ["guest_name", "room_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_bookings",
            "description": "Retrieve existing bookings with optional filters such as status, today's bookings only, or guest name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter by status, e.g. 'confirmed' or 'cancelled'."
                    },
                    "today_only": {
                        "type": "boolean",
                        "description": "Set to true to only view bookings active today."
                    },
                    "guest_name": {
                        "type": "string",
                        "description": "Filter bookings by guest name."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_booking",
            "description": "Cancel an existing hotel booking using the booking ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_id": {
                        "type": "integer",
                        "description": "The integer ID of the booking to cancel."
                    }
                },
                "required": ["booking_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_guests",
            "description": "Return guest information. Can search by guest name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Guest name or partial name to search for."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_rooms",
            "description": "Return information and status for all hotel rooms. Can filter by room type or status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "room_type": {
                        "type": "string",
                        "description": "Filter by room type, e.g. 'Single', 'Double', 'Deluxe'."
                    },
                    "status": {
                        "type": "string",
                        "description": "Filter by status: 'available', 'occupied', or 'maintenance'."
                    }
                },
                "required": []
            }
        }
    }
]


def execute_tool(tool_name: str, arguments: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """Execute the specified tool by name with arguments and database session."""
    today = datetime.date.today()
    default_check_in = today.isoformat()
    default_check_out = (today + datetime.timedelta(days=1)).isoformat()

    if tool_name == "check_room_availability":
        return check_room_availability(
            db=db,
            room_type=arguments.get("room_type"),
            check_in=arguments.get("check_in"),
            check_out=arguments.get("check_out")
        )
    elif tool_name == "create_booking":
        return create_booking(
            db=db,
            guest_name=arguments.get("guest_name", "Guest"),
            room_number=str(arguments.get("room_number")),
            check_in=arguments.get("check_in") or default_check_in,
            check_out=arguments.get("check_out") or default_check_out,
            guest_email=arguments.get("guest_email"),
            guest_phone=arguments.get("guest_phone")
        )
    elif tool_name == "get_bookings":
        return get_bookings(
            db=db,
            status=arguments.get("status"),
            today_only=arguments.get("today_only", False),
            guest_name=arguments.get("guest_name")
        )
    elif tool_name == "cancel_booking":
        booking_id = arguments.get("booking_id")
        if booking_id is None:
            return {"success": False, "error": "booking_id is required."}
        try:
            booking_id = int(booking_id)
        except (ValueError, TypeError):
            return {"success": False, "error": f"Invalid booking_id: {booking_id}"}
        return cancel_booking(db=db, booking_id=booking_id)
    elif tool_name == "get_guests":
        return get_guests(
            db=db,
            name=arguments.get("name")
        )
    elif tool_name == "get_rooms":
        return get_rooms(
            db=db,
            room_type=arguments.get("room_type"),
            status=arguments.get("status")
        )
    else:
        return {"success": False, "error": f"Unknown tool '{tool_name}'"}
