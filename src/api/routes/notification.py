from fastapi import APIRouter, Query, HTTPException
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.db.models import Notification

router = APIRouter()

@router.get("/notifications/unread")
def get_unread_notifications(user_id: str = Query(...)):
    db = next(get_db())
    notes = (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.is_read == False)
        .order_by(Notification.created_at.desc())
        .all()
    )
    return [
        dict(
            id=str(n.id),
            type=n.type,
            title=n.title,
            message=n.message,
            metadata=n.metadata,
            is_read=n.is_read,
            created_at=n.created_at
        )
        for n in notes
    ]

@router.patch("/notifications/{note_id}/mark-read")
def mark_notification_read(note_id: str):
    db = next(get_db())
    note = db.query(Notification).filter(Notification.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Notification not found")
    note.is_read = True
    db.commit()
    return {"status": "success", "message": "Notification marked as read"}
