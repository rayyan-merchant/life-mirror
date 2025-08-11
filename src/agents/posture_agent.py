import os
from .base_agent import BaseAgent, AgentInput, AgentOutput

class PostureAgent(BaseAgent):
    name = "posture_agent"
    output_schema = AgentOutput

    def run(self, input: AgentInput) -> AgentOutput:
        mode = os.getenv("LIFEMIRROR_MODE", "mock")

        if mode == "mock":
            result = AgentOutput(
                success=True,
                data={
                    "posture": "upright",
                    "alignment_score": 8.2,
                    "improvement_tips": ["Relax shoulders", "Keep chin level"]
                }
            )
        else:
            result = AgentOutput(success=False, data={}, error="Not implemented")

        self._trace(input.dict(), result.dict())
        return result
