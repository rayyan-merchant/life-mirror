import os
from typing import List
from pydantic import BaseModel, Field, ValidationError
from src.agents.base_agent import BaseAgent, AgentInput, AgentOutput
from src.services.perception import PerceptionAggregator
from src.db.session import get_db
from src.agents.perception_history_agent import PerceptionHistoryAgent

class FixitOutput(BaseModel):
    quick_tips: List[str] = Field(..., description="3–5 quick, actionable improvement tips.")
    detailed_plan: str = Field(..., description="Detailed strategy for improving social vibe.")
    focus_areas: List[str] = Field(..., description="Key areas to work on.")

class FixitAgent(BaseAgent):
    name = "fixit_agent"
    output_schema = FixitOutput

    def run(self, input: AgentInput) -> AgentOutput:
        mode = os.getenv("LIFEMIRROR_MODE", "mock")
        user_id = input.data["user_id"]

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
        agg = PerceptionAggregator(db)
        perception_data = agg.build_profile(input.data["media_id"])

        # Get history trends for better suggestions
        history_agent = PerceptionHistoryAgent()
        history_res = history_agent.run(AgentInput(media_id=0, url=None, data={"user_id": user_id}))
        history_data = history_res.data if history_res.success else {}

        prompt = f"""
        You are a social improvement assistant.
        Using the latest perception data and optional history trends below,
        generate a JSON object with:
        - quick_tips: list of 3–5 short, actionable tips
        - detailed_plan: a clear paragraph of improvement strategies
        - focus_areas: list of key attributes to work on

        Perception data:
        {perception_data}

        History trends:
        {history_data}
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
