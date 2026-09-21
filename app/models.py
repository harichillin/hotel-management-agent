from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class Guest(Base):
    __tablename__ = "guests"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)

    bookings = relationship("Booking", back_populates="guest", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
        }


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    room_number = Column(String, unique=True, nullable=False, index=True)
    room_type = Column(String, nullable=False, index=True)  # Single, Double, Deluxe
    price_per_night = Column(Float, nullable=False)
    status = Column(String, default="available", nullable=False)  # available, occupied, maintenance

    bookings = relationship("Booking", back_populates="room")

    def to_dict(self):
        return {
            "id": self.id,
            "room_number": self.room_number,
            "room_type": self.room_type,
            "price_per_night": self.price_per_night,
            "status": self.status,
        }


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    guest_id = Column(Integer, ForeignKey("guests.id"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    check_in = Column(String, nullable=False)   # YYYY-MM-DD
    check_out = Column(String, nullable=False)  # YYYY-MM-DD
    status = Column(String, default="confirmed", nullable=False)  # confirmed, cancelled

    guest = relationship("Guest", back_populates="bookings")
    room = relationship("Room", back_populates="bookings")

    def to_dict(self):
        return {
            "id": self.id,
            "guest_id": self.guest_id,
            "guest_name": self.guest.name if self.guest else None,
            "room_id": self.room_id,
            "room_number": self.room.room_number if self.room else None,
            "room_type": self.room.room_type if self.room else None,
            "check_in": self.check_in,
            "check_out": self.check_out,
            "status": self.status,
        }
