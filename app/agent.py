import os
import json
import re
import datetime
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from app.tools import HOTEL_TOOLS_DEFINITIONS, execute_tool

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

SYSTEM_PROMPT = f"""You are a helpful, professional, and concise Hotel Management AI Agent.
Current Date: {datetime.date.today().isoformat()}

You have access to tools to manage hotel rooms, guests, and bookings:
- check_room_availability: checks which rooms are available, optionally filter by room_type (Single, Double, Deluxe) and dates.
- create_booking: creates a new booking for a guest and room.
- get_bookings: lists existing bookings, can filter by status or today_only.
- cancel_booking: cancels a booking by booking ID.
- get_guests: retrieves guest records by name.
- get_rooms: lists all rooms and their current statuses.

Always use your tools to query or mutate the hotel database.
Answer the user's inquiry clearly and concisely. Format room and booking lists neatly.
"""

def _fallback_parse_request(user_message: str, db: Session) -> Tuple[str, List[str]]:
    """
    Lightweight rule-based fallback when OPENAI_API_KEY is not configured or unavailable.
    Provides immediate zero-config demonstration for standard queries.
    """
    msg_lower = user_message.lower().strip()
    tools_called = []

    # 1. Check availability
    if "available" in msg_lower or "availability" in msg_lower:
        room_type = None
        for rt in ["deluxe", "double", "single"]:
            if rt in msg_lower:
                room_type = rt.capitalize()
                break
        tools_called.append("check_room_availability")
        res = execute_tool("check_room_availability", {"room_type": room_type}, db)
        rooms = res.get("rooms", [])
        if not rooms:
            type_str = f" {room_type}" if room_type else ""
            return f"No{type_str} rooms are currently available.", tools_called
        
        lines = [f"Found {len(rooms)} available room(s):"]
        for r in rooms:
            lines.append(f"• Room {r['room_number']} ({r['room_type']}) - ${r['price_per_night']:.2f}/night")
        return "\n".join(lines), tools_called

    # 2. Cancel booking (e.g. "Cancel booking 5" or "Cancel booking #1")
    cancel_match = re.search(r"cancel\s+(?:booking\s+)?#?(\d+)", msg_lower)
    if cancel_match:
        booking_id = int(cancel_match.group(1))
        tools_called.append("cancel_booking")
        res = execute_tool("cancel_booking", {"booking_id": booking_id}, db)
        if res.get("success"):
            return res.get("message", f"Booking #{booking_id} cancelled successfully."), tools_called
        else:
            return f"Failed to cancel booking #{booking_id}: {res.get('error')}", tools_called

    # 3. Create booking (e.g. "Book room 101 for John" or "Book 201 for Alice Smith")
    book_match = re.search(r"book\s+(?:room\s+)?(\w+)\s+for\s+([a-zA-Z\s]+)", msg_lower)
    if book_match:
        room_num = book_match.group(1).strip()
        guest_name = book_match.group(2).strip().title()
        tools_called.append("create_booking")
        res = execute_tool("create_booking", {"room_number": room_num, "guest_name": guest_name}, db)
        if res.get("success"):
            return (
                f"Booking confirmed! Booking ID #{res['booking_id']} created for {res['guest_name']} "
                f"in Room {res['room_number']} ({res['room_type']}) from {res['check_in']} to {res['check_out']}."
            ), tools_called
        else:
            return f"Could not complete booking: {res.get('error')}", tools_called

    # 4. Show today's bookings
    if "today" in msg_lower and "booking" in msg_lower:
        tools_called.append("get_bookings")
        res = execute_tool("get_bookings", {"today_only": True}, db)
        bookings = res.get("bookings", [])
        if not bookings:
            return "There are no bookings scheduled for today.", tools_called
        lines = [f"Today's active bookings ({len(bookings)}):"]
        for b in bookings:
            lines.append(f"• Booking #{b['id']}: Room {b['room_number']} ({b['room_type']}) - Guest: {b['guest_name']} [{b['status'].upper()}] ({b['check_in']} to {b['check_out']})")
        return "\n".join(lines), tools_called

    # 5. Show all bookings
    if "booking" in msg_lower:
        tools_called.append("get_bookings")
        res = execute_tool("get_bookings", {}, db)
        bookings = res.get("bookings", [])
        if not bookings:
            return "No bookings found in the system.", tools_called
        lines = [f"All Bookings ({len(bookings)}):"]
        for b in bookings:
            lines.append(f"• Booking #{b['id']}: Room {b['room_number']} ({b['room_type']}) - Guest: {b['guest_name']} [{b['status'].upper()}] ({b['check_in']} to {b['check_out']})")
        return "\n".join(lines), tools_called

    # 6. Show guest (e.g. "Show guest John" or "Find guest Alice" or "Show guests")
    if "guest" in msg_lower:
        name_match = re.search(r"(?:guest|guests)\s+([a-zA-Z]+)", msg_lower)
        name = name_match.group(1).strip() if name_match else None
        tools_called.append("get_guests")
        res = execute_tool("get_guests", {"name": name}, db)
        guests = res.get("guests", [])
        if not guests:
            return f"No guests found matching '{name}'." if name else "No guests found.", tools_called
        lines = [f"Guests ({len(guests)}):"]
        for g in guests:
            lines.append(f"• ID #{g['id']}: {g['name']} | Email: {g['email']} | Phone: {g['phone']}")
        return "\n".join(lines), tools_called

    # 7. Show rooms
    if "room" in msg_lower:
        tools_called.append("get_rooms")
        res = execute_tool("get_rooms", {}, db)
        rooms = res.get("rooms", [])
        lines = [f"Hotel Rooms ({len(rooms)}):"]
        for r in rooms:
            lines.append(f"• Room {r['room_number']} ({r['room_type']}) - ${r['price_per_night']:.2f}/night [{r['status'].upper()}]")
        return "\n".join(lines), tools_called

    return (
        "I can help you with hotel management! You can ask me:\n"
        "• 'Show available rooms'\n"
        "• 'Are there any deluxe rooms available?'\n"
        "• 'Book room 101 for John'\n"
        "• 'Show all bookings'\n"
        "• 'Cancel booking 1'\n"
        "• 'Show guest John'\n"
        "• 'Show all rooms'",
        tools_called
    )


def run_agent_chat(user_message: str, db: Session) -> Dict[str, Any]:
    """
    Run the Hotel Management AI Agent on a user's natural language message.
    Uses OpenAI-compatible LLM tool-calling if OPENAI_API_KEY is configured,
    or smoothly falls back to the intelligent pattern parser.
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    
    # If no real API key is set, use fallback parser
    if not api_key or api_key.startswith("your-") or api_key == "placeholder":
        response_text, tools_called = _fallback_parse_request(user_message, db)
        return {
            "response": response_text,
            "tools_called": tools_called,
            "mode": "fallback"
        }

    # Attempt OpenAI-compatible LLM tool calling
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=api_key,
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]

        tools_called = []
        max_iterations = 4

        for _ in range(max_iterations):
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                tools=HOTEL_TOOLS_DEFINITIONS,
                tool_choice="auto",
                temperature=0.2
            )

            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls

            if not tool_calls:
                # LLM finished with final response
                return {
                    "response": response_message.content or "Request completed.",
                    "tools_called": tools_called,
                    "mode": "llm"
                }

            # Convert response message to dict for OpenAI message history
            messages.append(response_message)

            for tool_call in tool_calls:
                fn_name = tool_call.function.name
                tools_called.append(fn_name)
                try:
                    fn_args = json.loads(tool_call.function.arguments)
                except Exception:
                    fn_args = {}

                tool_result = execute_tool(fn_name, fn_args, db)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": fn_name,
                    "content": json.dumps(tool_result)
                })

        return {
            "response": "Agent reached maximum tool-call limit.",
            "tools_called": tools_called,
            "mode": "llm"
        }

    except Exception as e:
        # If OpenAI API fails (e.g., bad key, network issue, rate limit), fallback gracefully
        response_text, tools_called = _fallback_parse_request(user_message, db)
        return {
            "response": f"{response_text}\n\n*(Note: LLM call encountered: {str(e)[:120]}. Handled via local tool engine.)*",
            "tools_called": tools_called,
            "mode": "fallback_error"
        }
