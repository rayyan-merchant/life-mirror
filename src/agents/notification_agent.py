from typing import Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from src.agents.base_agent import BaseAgent, AgentInput, AgentOutput
from src.agents.social_graph_agent import SocialGraphAgent
from src.db.session import get_db
from src.db.models import User, Media, Notification
from datetime import datetime, timedelta
import uuid

class NotificationData(BaseModel):
    type: str
    title: str
    message: str
    metadata: dict

class NotificationAgent(BaseAgent):
    name = "notification_agent"
    output_schema = NotificationData

    def _store_notification(self, db: Session, user_id: str, note: NotificationData):
        db.add(Notification(
            id=uuid.uuid4(),
            user_id=user_id,
            type=note.type,
            title=note.title,
            message=note.message,
            metadata=note.metadata
        ))
        db.commit()

    def run(self, input: AgentInput) -> AgentOutput:
        user_id = input.data["user_id"]
        db = next(get_db())

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return AgentOutput(success=False, error="User not found")

        # ✅ 1. Improvement reminder after 14 days
        latest_media = (
            db.query(Media)
            .filter(Media.user_id == user_id)
            .order_by(Media.created_at.desc())
            .first()
        )
        if latest_media and latest_media.created_at < datetime.utcnow() - timedelta(days=14):
            note = NotificationData(
                type="improvement_reminder",
                title="Time for a new check-in!",
                message="It’s been 2 weeks since your last analysis. Want to upload a new photo or video?",
                metadata={"media_id": str(latest_media.id)}
            )
            self._store_notification(db, user_id, note)

        # ✅ 2. Social Graph percentile change
        sg = SocialGraphAgent().run(AgentInput(data={"user_id": user_id}))
        if sg.success and not sg.data.get("cold_start"):
            current_percentile = sg.data["percentile"]["overall"]
            last_note = (
                db.query(Notification)
                .filter(Notification.user_id == user_id, Notification.type == "percentile_update")
                .order_by(Notification.created_at.desc())
                .first()
            )
            if not last_note or last_note.metadata.get("percentile") != current_percentile:
                note = NotificationData(
                    type="percentile_update",
                    title="Your vibe ranking has changed!",
                    message=f"Your overall percentile is now {current_percentile}%",
                    metadata={"percentile": current_percentile}
                )
                self._store_notification(db, user_id, note)

        # ✅ 3. Similar user uploaded new content
        if sg.success and sg.data.get("similar_users"):
            for sim_user in sg.data["similar_users"]:
                sim_media = (
                    db.query(Media)
                    .filter(Media.user_id == sim_user["user_id"])
                    .order_by(Media.created_at.desc())
                    .first()
                )
                if sim_media and sim_media.created_at > datetime.utcnow() - timedelta(days=2):
                    note = NotificationData(
                        type="similar_user_activity",
                        title=f"{sim_user['alias']} posted something new!",
                        message="A similar user has uploaded new content — check it out and see how you compare.",
                        metadata={"similar_user_id": sim_user["user_id"], "media_id": str(sim_media.id)}
                    )
                    self._store_notification(db, user_id, note)

        return AgentOutput(success=True, data={"status": "notifications checked"})
