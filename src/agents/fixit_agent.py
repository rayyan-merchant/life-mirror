import os
from typing import List, Optional
from pydantic import BaseModel, Field, ValidationError
from src.agents.base_agent import BaseAgent, AgentInput, AgentOutput
from src.services.perception import PerceptionAggregator
from src.db.session import get_db
from src.agents.perception_history_agent import PerceptionHistoryAgent
from src.db.models import Media
from sqlalchemy.orm import Session


class FixitOutput(BaseModel):
    quick_tips: List[str] = Field(..., description="3–5 quick, actionable improvement tips.")
    detailed_plan: str = Field(..., description="Detailed strategy for improving social vibe.")
    focus_areas: List[str] = Field(..., description="Key areas to work on.")


class FixitAgent(BaseAgent):
    name = "fixit_agent"
    output_schema = FixitOutput

    def _get_recent_perception(self, db: Session, user_id: int, recent_limit: int = 5):
        """
        Fetch perception data from the last `recent_limit` media items for the user.
        """
        recent_media = (
            db.query(Media)
            .filter(Media.user_id == user_id)
            .order_by(Media.created_at.desc())
            .limit(recent_limit)
            .all()
        )

        return [
            {
                "media_id": m.id,
                "timestamp": m.created_at.isoformat(),
                "social": m.metadata.get("social", {})
            }
            for m in recent_media
            if m.metadata and "social" in m.metadata
        ]

    def run(self, input: AgentInput) -> AgentOutput:
        mode = os.getenv("LIFEMIRROR_MODE", "mock")
        user_id = input.data["user_id"]
        recent_limit = input.data.get("recent_limit", 5)

        if mode == "mock":
            result = AgentOutput(success=True, data={
                "quick_tips": [
                    "Smile naturally in photos.",
                    "Maintain better posture.",
                    "Wear brighter colors."
                ],
                "detailed_plan": "Focus on expressing warmth through eye contact and open body language. Try experimenting with casual but polished outfits. Review past photos for posture and angle adjustments.",
                "focus_areas": ["posture", "color choice", "facial expression"]
            })
            self._trace(input.dict(), result.dict())
            return result

        # --- PROD MODE ---
        db = next(get_db())

        # Fetch recent perception (last N uploads)
        recent_perception = self._get_recent_perception(db, user_id, recent_limit=recent_limit)

        if not recent_perception:
            return AgentOutput(success=False, data={}, error="No recent perception data found.")

        # Get history trends to identify improved areas
        history_agent = PerceptionHistoryAgent()
        history_res = history_agent.run(AgentInput(media_id=0, url=None, data={"user_id": user_id}))
        history_data = history_res.data if history_res.success else {}

        improved_areas = set(history_data.get("improvement_tags", []))

        # Filter out improvement areas from focus
        filtered_data = {
            "recent_perception": recent_perception,
            "history_summary": {
                "trend_summary": history_data.get("trend_summary", ""),
                "decline_tags": history_data.get("decline_tags", []),
                "score_trend": history_data.get("score_trend", []),
            },
            "ignore_areas": list(improved_areas)
        }

        prompt = f"""
        You are a social improvement assistant.
        Using the recent perception data (last {recent_limit} media items) and history trends below,
        generate a JSON object with:
        - quick_tips: 3–5 short, actionable tips
        - detailed_plan: a clear paragraph of improvement strategies
        - focus_areas: areas to work on, excluding any in 'ignore_areas'.

        Data:
        {filtered_data}
        """

        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a perception improvement and personal presentation coach."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )

            raw_json = resp.choices[0].message["content"]

            try:
                parsed = FixitOutput.model_validate_json(raw_json)
            except ValidationError as ve:
                return AgentOutput(success=False, data={}, error=f"Validation failed: {ve}")

            result = AgentOutput(success=True, data=parsed.dict())
            self._trace(input.dict(), result.dict())
            return result

        except Exception as e:
            return AgentOutput(success=False, data={}, error=str(e))
