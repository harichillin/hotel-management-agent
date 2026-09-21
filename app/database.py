import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, Room, Guest, Booking

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./hotel.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Create all tables and seed sample data if not already present."""
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Seed rooms if empty
        if db.query(Room).count() == 0:
            sample_rooms = [
                Room(room_number="101", room_type="Single", price_per_night=50.0, status="available"),
                Room(room_number="102", room_type="Single", price_per_night=50.0, status="available"),
                Room(room_number="201", room_type="Double", price_per_night=80.0, status="occupied"),
                Room(room_number="202", room_type="Double", price_per_night=80.0, status="available"),
                Room(room_number="301", room_type="Deluxe", price_per_night=150.0, status="available"),
                Room(room_number="302", room_type="Deluxe", price_per_night=150.0, status="available"),
            ]
            db.add_all(sample_rooms)
            db.commit()

        # Seed guests if empty
        if db.query(Guest).count() == 0:
            sample_guests = [
                Guest(name="John Doe", email="john.doe@example.com", phone="+1-555-0101"),
                Guest(name="Alice Smith", email="alice.smith@example.com", phone="+1-555-0102"),
                Guest(name="Robert Johnson", email="robert.j@example.com", phone="+1-555-0103"),
            ]
            db.add_all(sample_guests)
            db.commit()

        # Seed an initial booking for room 201 if no bookings exist
        if db.query(Booking).count() == 0:
            guest_john = db.query(Guest).filter(Guest.name.ilike("%John%")).first()
            room_201 = db.query(Room).filter(Room.room_number == "201").first()
            if guest_john and room_201:
                sample_booking = Booking(
                    guest_id=guest_john.id,
                    room_id=room_201.id,
                    check_in="2026-09-20",
                    check_out="2026-09-23",
                    status="confirmed"
                )
                db.add(sample_booking)
                db.commit()
    finally:
        db.close()
