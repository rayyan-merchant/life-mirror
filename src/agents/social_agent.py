import os
from src.agents.base_agent import BaseAgent, AgentInput, AgentOutput
from src.services.perception import PerceptionAggregator
from src.db.session import get_db
from pydantic import BaseModel, Field, ValidationError
from typing import List

class SocialOutput(BaseModel):
    summary_text: str = Field(..., description="2–3 sentence natural language summary.")
    tags: List[str] = Field(..., description="List of 3–8 personality/social style tags.")
    social_score: float = Field(..., ge=0, le=10, description="Social vibe score (0–10).")

class SocialAgent(BaseAgent):
    name = "social_agent"
    output_schema = SocialOutput

    def run(self, input: AgentInput) -> AgentOutput:
        mode = os.getenv("LIFEMIRROR_MODE", "mock")

        if mode == "mock":
            result = AgentOutput(success=True, data={
                "summary_text": "You look confident and approachable, with a casual yet put-together style.",
                "tags": ["confident", "approachable", "stylish", "friendly"],
                "social_score": 8.2
            })
            self._trace(input.dict(), result.dict())
            return result

        # --- PROD MODE ---
        perception_data = None
        if "perception_data" in input.data:
            perception_data = input.data["perception_data"]
        elif "media_id" in input.data:
            db = next(get_db())
            agg = PerceptionAggregator(db)
            perception_data = agg.build_profile(input.data["media_id"])
            if "error" in perception_data:
                return AgentOutput(success=False, data={}, error=perception_data["error"])

        prompt = f"""
        You are a social perception AI. Given the structured perception data below,
        return a JSON object with:
        - summary_text: 2–3 sentence natural-language summary
        - tags: list of 3–8 personality/social style tags
        - social_score: float from 0 to 10

        Perception data:
        {perception_data}
        """

        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a socially intelligent perception analysis assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}  # ✅ Forces JSON output
            )

            raw_json = resp.choices[0].message["content"]

            try:
                parsed = SocialOutput.model_validate_json(raw_json)  # ✅ Guardrails via Pydantic
            except ValidationError as ve:
                return AgentOutput(success=False, data={}, error=f"Validation failed: {ve}")

            result = AgentOutput(success=True, data=parsed.dict())
            self._trace(input.dict(), result.dict())
            return result

        except Exception as e:
            return AgentOutput(success=False, data={}, error=str(e))
