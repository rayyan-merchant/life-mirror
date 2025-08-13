from fastapi import APIRouter, Query
from src.db.session import get_db
from src.db.models import Notification
from sqlalchemy.orm import Session

router = APIRouter()

@router.get("/notifications")
def get_notifications(user_id: str = Query(...)):
    db = next(get_db())
    notes = db.query(Notification).filter(Notification.user_id == user_id).order_by(Notification.created_at.desc()).all()
    return [dict(
        id=str(n.id),
        type=n.type,
        title=n.title,
        message=n.message,
        metadata=n.metadata,
        is_read=n.is_read,
        created_at=n.created_at
    ) for n in notes]
