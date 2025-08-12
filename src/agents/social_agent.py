# src/agents/social_agent.py
import os
from src.agents.base_agent import BaseAgent, AgentInput, AgentOutput
from src.services.perception import PerceptionAggregator
from src.db.session import get_db
from pydantic import BaseModel, Field
from typing import List

class SocialOutput(BaseModel):
    summary_text: str = Field(..., description="Natural language social perception summary.")
    tags: List[str] = Field(..., description="List of 3–8 personality/social style tags.")
    social_score: float = Field(..., description="Overall social vibe score (0–10).")

class SocialAgent(BaseAgent):
    name = "social_agent"
    output_schema = SocialOutput

    def run(self, input: AgentInput) -> AgentOutput:
        """
        input.data should contain either:
        - media_id (int), OR
        - perception_data (dict from PerceptionAggregator)
        """
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
        # Get perception data
        perception_data = None
        if "perception_data" in input.data:
            perception_data = input.data["perception_data"]
        elif "media_id" in input.data:
            db = next(get_db())
            agg = PerceptionAggregator(db)
            perception_data = agg.build_profile(input.data["media_id"])
            if "error" in perception_data:
                return AgentOutput(success=False, data={}, error=perception_data["error"])

        # Prepare prompt for LLM
        prompt = f"""
        You are a social perception AI. Analyze the given structured perception data
        and provide:
        1. A 2-3 sentence natural language summary describing the person's vibe.
        2. A list of 3–8 tags describing their personality/social style.
        3. An overall social score (0–10).

        Perception data (JSON):
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
                temperature=0.7
            )
            text_output = resp.choices[0].message["content"]

            # Very simple parse — in production use JSON mode or Guardrails
            # For now: naive split
            summary = text_output.strip()
            # Could also implement JSON.parse with GPT
            # Placeholder — real guardrails JSON parsing recommended
            result = AgentOutput(success=True, data={
                "summary_text": summary,
                "tags": ["confident", "friendly"],  # Replace with real parsed tags
                "social_score": 7.5
            })
            self._trace(input.dict(), result.dict())
            return result

        except Exception as e:
            return AgentOutput(success=False, data={}, error=str(e))
