import os
from typing import List
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session
from src.agents.base_agent import BaseAgent, AgentInput, AgentOutput
from src.db.session import get_db
from src.db.models import Media
from src.agents.perception_history_agent import PerceptionHistoryAgent


class VibeAnalysisOutput(BaseModel):
    vibe_score: int = Field(..., description="Score from 0-100 representing overall vibe quality.")
    vibe_tags: List[str] = Field(..., description="List of 3-6 words describing the current vibe.")
    personality_summary: str = Field(..., description="Short description of perceived personality.")
    strengths: List[str] = Field(..., description="List of current strengths.")
    improvement_areas: List[str] = Field(..., description="List of areas to improve.")


class VibeAnalysisAgent(BaseAgent):
    name = "vibe_analysis_agent"
    output_schema = VibeAnalysisOutput

    def _get_recent_perception(self, db: Session, user_id: int, recent_limit: int = 5):
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
                "social": m.metadata.get("social", {}),
                "fixit_suggestions": m.metadata.get("fixit_suggestions"),
                "reverse_analysis": m.metadata.get("reverse_analysis")
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
                "vibe_score": 82,
                "vibe_tags": ["confident", "approachable", "stylish"],
                "personality_summary": "You project confidence with a friendly demeanor and a sense of style.",
                "strengths": ["Strong eye contact", "Balanced posture", "Fashion sense"],
                "improvement_areas": ["Experiment with more vibrant colors", "Add variety to poses"]
            })
            self._trace(input.dict(), result.dict())
            return result

        # --- PROD MODE ---
        db = next(get_db())
        recent_perception = self._get_recent_perception(db, user_id, recent_limit=recent_limit)

        if not recent_perception:
            return AgentOutput(success=False, data={}, error="No recent perception data found.")

        # Get history trends
        history_agent = PerceptionHistoryAgent()
        history_res = history_agent.run(AgentInput(media_id=0, url=None, data={"user_id": user_id}))
        history_data = history_res.data if history_res.success else {}

        combined_data = {
            "recent_perception": recent_perception,
            "history_summary": history_data
        }

        prompt = f"""
        You are a social vibe evaluator.
        Using the provided data, produce:
        - vibe_score: integer 0-100
        - vibe_tags: 3-6 short descriptive tags
        - personality_summary: 1-2 sentence description
        - strengths: list of current strengths
        - improvement_areas: list of key improvement points

        Data:
        {combined_data}
        """

        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert in social perception and personal branding."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )

            raw_json = resp.choices[0].message["content"]

            try:
                parsed = VibeAnalysisOutput.model_validate_json(raw_json)
            except ValidationError as ve:
                return AgentOutput(success=False, data={}, error=f"Validation failed: {ve}")

            result = AgentOutput(success=True, data=parsed.dict())
            self._trace(input.dict(), result.dict())
            return result

        except Exception as e:
            return AgentOutput(success=False, data={}, error=str(e))
