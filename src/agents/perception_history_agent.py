import os
from typing import List
from datetime import datetime
from pydantic import BaseModel, Field, ValidationError
from src.agents.base_agent import BaseAgent, AgentInput, AgentOutput
from src.db.session import get_db
from src.db.models import Media
from sqlalchemy.orm import Session

class PerceptionHistoryOutput(BaseModel):
    trend_summary: str = Field(..., description="Natural language summary of perception changes over time.")
    score_trend: List[dict] = Field(..., description="List of {'timestamp': ISO date, 'score': float}.")
    improvement_tags: List[str] = Field(..., description="Areas where the user improved.")
    decline_tags: List[str] = Field(..., description="Areas where the user declined.")

class PerceptionHistoryAgent(BaseAgent):
    name = "perception_history_agent"
    output_schema = PerceptionHistoryOutput

    def _fetch_user_media_data(self, db: Session, user_id: int):
        media_items = (
            db.query(Media)
            .filter(Media.user_id == user_id)
            .order_by(Media.created_at.asc())
            .all()
        )
        history = []
        for m in media_items:
            if m.metadata and "social" in m.metadata:
                history.append({
                    "timestamp": m.created_at.isoformat(),
                    "score": m.metadata["social"].get("social_score", None),
                    "tags": m.metadata["social"].get("tags", [])
                })
        return history

    def run(self, input: AgentInput) -> AgentOutput:
        mode = os.getenv("LIFEMIRROR_MODE", "mock")
        user_id = input.data["user_id"]

        if mode == "mock":
            result = AgentOutput(success=True, data={
                "trend_summary": "Your social vibe has become more confident and approachable over time.",
                "score_trend": [
                    {"timestamp": "2025-01-01T10:00:00", "score": 6.5},
                    {"timestamp": "2025-02-15T10:00:00", "score": 7.2},
                    {"timestamp": "2025-03-30T10:00:00", "score": 8.0}
                ],
                "improvement_tags": ["confidence", "friendliness"],
                "decline_tags": ["eye contact"]
            })
            self._trace(input.dict(), result.dict())
            return result

        # --- PROD MODE ---
        db = next(get_db())
        history = self._fetch_user_media_data(db, user_id)

        if not history:
            return AgentOutput(success=False, data={}, error="No history found for user.")

        prompt = f"""
        Analyze the following chronological perception history and return a JSON object with:
        - trend_summary: a short narrative of overall changes
        - score_trend: list of timestamp→score pairs
        - improvement_tags: areas where user improved
        - decline_tags: areas where user declined

        History data:
        {history}
        """

        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a social perception trend analysis assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )

            raw_json = resp.choices[0].message["content"]

            try:
                parsed = PerceptionHistoryOutput.model_validate_json(raw_json)
            except ValidationError as ve:
                return AgentOutput(success=False, data={}, error=f"Validation failed: {ve}")

            result = AgentOutput(success=True, data=parsed.dict())
            self._trace(input.dict(), result.dict())
            return result

        except Exception as e:
            return AgentOutput(success=False, data={}, error=str(e))
