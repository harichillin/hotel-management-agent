from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Guest
from app.schemas import GuestResponse

router = APIRouter(prefix="/guests", tags=["Guests"])

@router.get("", response_model=List[GuestResponse])
def get_guests(
    name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Guest)
    if name:
        query = query.filter(Guest.name.ilike(f"%{name.strip()}%"))
    return query.order_by(Guest.id).all()
