"""
Automated test suite for Hotel Management Agent.
Tests all 6 tools, database operations, agent chat, and FastAPI REST endpoints.
"""
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(__file__))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.database import init_db, SessionLocal, engine
from app.models import Base, Room, Guest, Booking
from app.tools import (
    check_room_availability,
    create_booking,
    get_bookings,
    cancel_booking,
    get_guests,
    get_rooms,
    execute_tool
)
from app.agent import run_agent_chat
from fastapi.testclient import TestClient
from app.main import app

def run_tests():
    print("--- 1. Testing Database Initialization & Seeding ---")
    init_db()
    db = SessionLocal()
    
    rooms = db.query(Room).all()
    guests = db.query(Guest).all()
    bookings = db.query(Booking).all()

    print(f"Loaded {len(rooms)} rooms, {len(guests)} guests, {len(bookings)} bookings.")
    assert len(rooms) >= 6, f"Expected at least 6 rooms, got {len(rooms)}"
    assert len(guests) >= 3, f"Expected at least 3 guests, got {len(guests)}"
    assert len(bookings) >= 1, f"Expected at least 1 booking, got {len(bookings)}"
    print("✓ DB Initialization & Seeding Passed.")

    print("\n--- 2. Testing the 6 Agent Tools ---")
    
    # Tool 1: check_room_availability
    res1 = check_room_availability(db)
    assert res1["success"] is True
    print(f"Tool 1 check_room_availability: found {res1['available_count']} available rooms.")
    
    res1_deluxe = check_room_availability(db, room_type="Deluxe")
    assert res1_deluxe["success"] is True
    assert all(r["room_type"] == "Deluxe" for r in res1_deluxe["rooms"])
    print(f"Tool 1 (Deluxe filter): {res1_deluxe['available_count']} deluxe rooms available.")

    # Tool 2: create_booking
    res2 = create_booking(
        db,
        guest_name="Test Customer",
        room_number="301",
        check_in="2026-10-01",
        check_out="2026-10-05"
    )
    assert res2["success"] is True
    test_booking_id = res2["booking_id"]
    print(f"Tool 2 create_booking: created booking #{test_booking_id} for Room 301.")

    # Test conflict prevention
    res2_conflict = create_booking(
        db,
        guest_name="Another Guest",
        room_number="301",
        check_in="2026-10-02",
        check_out="2026-10-04"
    )
    assert res2_conflict["success"] is False
    print("Tool 2 conflict detection verified:", res2_conflict["error"])

    # Tool 3: get_bookings
    res3 = get_bookings(db)
    assert res3["success"] is True
    assert res3["total"] >= 2
    print(f"Tool 3 get_bookings: found {res3['total']} bookings.")

    # Tool 4: cancel_booking
    res4 = cancel_booking(db, booking_id=test_booking_id)
    assert res4["success"] is True
    print(f"Tool 4 cancel_booking: cancelled booking #{test_booking_id}.")

    # Tool 5: get_guests
    res5 = get_guests(db, name="John")
    assert res5["success"] is True
    assert len(res5["guests"]) >= 1
    print(f"Tool 5 get_guests: found {len(res5['guests'])} guest(s) matching 'John'.")

    # Tool 6: get_rooms
    res6 = get_rooms(db)
    assert res6["success"] is True
    assert len(res6["rooms"]) >= 6
    print(f"Tool 6 get_rooms: retrieved {len(res6['rooms'])} rooms.")

    # Tool Dispatcher
    disp_res = execute_tool("check_room_availability", {"room_type": "Single"}, db)
    assert disp_res["success"] is True
    print(f"Tool Dispatcher: verified check_room_availability dispatch.")

    db.close()
    print("✓ All 6 Tools Passed.")

    print("\n--- 3. Testing Agent Natural-Language Queries ---")
    db = SessionLocal()
    test_queries = [
        "Show available rooms",
        "Are there any deluxe rooms available?",
        "Book room 101 for John",
        "Show all bookings",
        "Cancel booking 1",
        "Show guest John",
        "Show today's bookings",
        "Show all rooms"
    ]

    for q in test_queries:
        agent_res = run_agent_chat(q, db)
        assert "response" in agent_res
        assert len(agent_res["response"]) > 0
        print(f"Query: '{q}' -> Response length: {len(agent_res['response'])}, Tools: {agent_res.get('tools_called')}")

    db.close()
    print("✓ Agent Natural-Language Queries Passed.")

    print("\n--- 4. Testing FastAPI Endpoints ---")
    client = TestClient(app)

    # Test GET /
    r_home = client.get("/")
    assert r_home.status_code == 200
    print("GET / status:", r_home.status_code)

    # Test GET /rooms
    r_rooms = client.get("/rooms")
    assert r_rooms.status_code == 200
    assert len(r_rooms.json()) >= 6
    print("GET /rooms count:", len(r_rooms.json()))

    # Test GET /guests
    r_guests = client.get("/guests")
    assert r_guests.status_code == 200
    assert len(r_guests.json()) >= 3
    print("GET /guests count:", len(r_guests.json()))

    # Test GET /bookings
    r_bookings = client.get("/bookings")
    assert r_bookings.status_code == 200
    print("GET /bookings count:", len(r_bookings.json()))

    # Test POST /bookings
    r_new_b = client.post("/bookings", json={
        "guest_name": "API Tester",
        "room_number": "102",
        "check_in": "2026-11-01",
        "check_out": "2026-11-05"
    })
    assert r_new_b.status_code == 201
    created_id = r_new_b.json()["id"]
    print(f"POST /bookings created ID #{created_id}")

    # Test DELETE /bookings/{id}
    r_del_b = client.delete(f"/bookings/{created_id}")
    assert r_del_b.status_code == 200
    print(f"DELETE /bookings/{created_id} succeeded")

    # Test POST /agent/chat
    r_chat = client.post("/agent/chat", json={"message": "Show available rooms"})
    assert r_chat.status_code == 200
    assert "response" in r_chat.json()
    print("POST /agent/chat responded:", r_chat.json()["response"][:60], "...")

    print("\n==========================================")
    print("🎉 ALL TESTS PASSED SUCCESSFULLY!")
    print("==========================================")

if __name__ == "__main__":
    run_tests()
