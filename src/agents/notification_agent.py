from typing import Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from src.agents.base_agent import BaseAgent, AgentInput, AgentOutput
from src.db.session import get_db
from src.db.models import User, Media
from datetime import datetime, timedelta

class NotificationData(BaseModel):
    type: str
    title: str
    message: str
    metadata: dict

class NotificationAgent(BaseAgent):
    name = "notification_agent"
    output_schema = NotificationData

    def run(self, input: AgentInput) -> AgentOutput:
        user_id = input.data["user_id"]
        db = next(get_db())

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return AgentOutput(success=False, error="User not found")

        # Example: Improvement reminder after 14 days
        latest_media = (
            db.query(Media)
            .filter(Media.user_id == user_id)
            .order_by(Media.created_at.desc())
            .first()
        )
        if latest_media and latest_media.created_at < datetime.utcnow() - timedelta(days=14):
            return AgentOutput(
                success=True,
                data=NotificationData(
                    type="improvement_reminder",
                    title="Time for a new check-in!",
                    message="It’s been 2 weeks since your last analysis. Want to upload a new photo or video?",
                    metadata={"media_id": str(latest_media.id)}
                ).dict()
            )

        return AgentOutput(success=False, error="No notification needed right now")
