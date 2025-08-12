import os
from typing import List
from pydantic import BaseModel, Field, ValidationError
from src.agents.base_agent import BaseAgent, AgentInput, AgentOutput
from src.services.perception import PerceptionAggregator
from src.db.session import get_db

class VibeComparisonOutput(BaseModel):
    summary: str = Field(..., description="Natural-language comparison summary of the two media items.")
    better_media_id: int = Field(..., description="Media ID with stronger positive social vibe (0 if equal).")
    comparison_tags: List[str] = Field(..., description="List of tags describing differences.")
    score_difference: float = Field(..., description="Absolute difference in social_score values.")

class VibeComparisonAgent(BaseAgent):
    name = "vibe_comparison_agent"
    output_schema = VibeComparisonOutput

    def run(self, input: AgentInput) -> AgentOutput:
        mode = os.getenv("LIFEMIRROR_MODE", "mock")

        # Expect: {"media_id_1": int, "media_id_2": int}
        media_id_1 = input.data["media_id_1"]
        media_id_2 = input.data["media_id_2"]

        if mode == "mock":
            result = AgentOutput(success=True, data={
                "summary": f"Media {media_id_1} exudes a warmer, more approachable vibe than media {media_id_2}.",
                "better_media_id": media_id_1,
                "comparison_tags": ["warmer", "friendlier", "more confident"],
                "score_difference": 1.5
            })
            self._trace(input.dict(), result.dict())
            return result

        # --- PROD MODE ---
        db = next(get_db())
        agg = PerceptionAggregator(db)

        profile_1 = agg.build_profile(media_id_1)
        profile_2 = agg.build_profile(media_id_2)

        prompt = f"""
        Compare the following two social perception profiles and return a JSON object with:
        - summary: a natural language comparison of the two
        - better_media_id: the ID with stronger positive social vibe (0 if equal)
        - comparison_tags: list of adjectives or descriptors contrasting them
        - score_difference: absolute difference in their social vibe scores (0–10 scale)

        Media {media_id_1} profile:
        {profile_1}

        Media {media_id_2} profile:
        {profile_2}
        """

        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a socially intelligent perception comparison assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )

            raw_json = resp.choices[0].message["content"]

            try:
                parsed = VibeComparisonOutput.model_validate_json(raw_json)
            except ValidationError as ve:
                return AgentOutput(success=False, data={}, error=f"Validation failed: {ve}")

            result = AgentOutput(success=True, data=parsed.dict())
            self._trace(input.dict(), result.dict())
            return result

        except Exception as e:
            return AgentOutput(success=False, data={}, error=str(e))
