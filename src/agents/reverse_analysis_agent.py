import os
from typing import List
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session
from src.agents.base_agent import BaseAgent, AgentInput, AgentOutput
from src.db.session import get_db
from src.db.models import Media
from src.agents.perception_history_agent import PerceptionHistoryAgent


class ReverseAnalysisOutput(BaseModel):
    goal: str = Field(..., description="The target perception/vibe provided by the user.")
    recommended_changes: List[str] = Field(..., description="List of actionable changes to reach the goal.")
    avoid_list: List[str] = Field(..., description="Things the user should avoid doing.")
    action_plan: str = Field(..., description="Detailed plan to reach the goal.")


class ReverseAnalysisAgent(BaseAgent):
    name = "reverse_analysis_agent"
    output_schema = ReverseAnalysisOutput

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
                "social": m.metadata.get("social", {})
            }
            for m in recent_media
            if m.metadata and "social" in m.metadata
        ]

    def run(self, input: AgentInput) -> AgentOutput:
        mode = os.getenv("LIFEMIRROR_MODE", "mock")
        user_id = input.data["user_id"]
        goal = input.data["goal"]
        recent_limit = input.data.get("recent_limit", 5)

        if mode == "mock":
            result = AgentOutput(success=True, data={
                "goal": goal,
                "recommended_changes": [
                    "Stand with shoulders back to project confidence.",
                    "Choose fitted blazers in bold colors.",
                    "Maintain steady eye contact with the camera."
                ],
                "avoid_list": [
                    "Avoid slouching.",
                    "Avoid dull or washed-out colors."
                ],
                "action_plan": "Adopt confident posture, wear bolder color choices, and practice intentional eye contact."
            })
            self._trace(input.dict(), result.dict())
            return result

        # --- PROD MODE ---
        db = next(get_db())
        recent_perception = self._get_recent_perception(db, user_id, recent_limit=recent_limit)

        if not recent_perception:
            return AgentOutput(success=False, data={}, error="No recent perception data found.")

        # Get history to avoid re-suggesting already improved areas
        history_agent = PerceptionHistoryAgent()
        history_res = history_agent.run(AgentInput(media_id=0, url=None, data={"user_id": user_id}))
        history_data = history_res.data if history_res.success else {}
        improved_areas = set(history_data.get("improvement_tags", []))

        filtered_data = {
            "goal": goal,
            "recent_perception": recent_perception,
            "history_summary": history_data,
            "ignore_areas": list(improved_areas)
        }

        prompt = f"""
        The user wants to achieve the following perception goal:
        "{goal}"

        Using the recent perception data and history trends below:
        - Recommend actionable changes in style, posture, expressions, and presentation.
        - Exclude areas listed in 'ignore_areas'.
        - Provide a list of things to avoid.
        - Provide a short, clear action plan.

        Data:
        {filtered_data}
        """

        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a perception transformation coach."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )

            raw_json = resp.choices[0].message["content"]

            try:
                parsed = ReverseAnalysisOutput.model_validate_json(raw_json)
            except ValidationError as ve:
                return AgentOutput(success=False, data={}, error=f"Validation failed: {ve}")

            result = AgentOutput(success=True, data=parsed.dict())
            self._trace(input.dict(), result.dict())
            return result

        except Exception as e:
            return AgentOutput(success=False, data={}, error=str(e))
