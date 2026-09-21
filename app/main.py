import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db, init_db
from app.schemas import ChatRequest, ChatResponse
from app.agent import run_agent_chat
from app.routes import rooms, guests, bookings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables and seed initial data
    init_db()
    yield

app = FastAPI(
    title="Hotel Management Agent",
    description="A simple, clean AI agent for hotel operations and management.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(rooms.router)
app.include_router(guests.router)
app.include_router(bookings.router)

# Agent Chat Endpoint
@app.post("/agent/chat", response_model=ChatResponse, tags=["Agent"])
def chat_with_agent(req: ChatRequest, db: Session = Depends(get_db)):
    result = run_agent_chat(user_message=req.message, db=db)
    return ChatResponse(
        response=result["response"],
        tools_called=result.get("tools_called", [])
    )

# Static files and Web UI
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", include_in_schema=False)
def serve_home():
    index_file = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Hotel Management Agent API is running. Visit /docs for documentation."}
