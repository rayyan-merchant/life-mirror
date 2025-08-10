import os
from .base_agent import BaseAgent, AgentInput, AgentOutput

class PostureAgent(BaseAgent):
    name = "posture_agent"

    def run(self, input: AgentInput) -> AgentOutput:
        mode = os.getenv("LIFEMIRROR_MODE", "mock")
        if mode == "mock":
            return AgentOutput(
                success=True,
                data={
                    "posture": "upright",
                    "alignment_score": 8.2,
                    "improvement_tips": ["Relax shoulders", "Keep chin level"]
                }
            )
        # TODO: integrate pose estimation model + LLM interpretation
        return AgentOutput(success=False, data={}, error="Prod mode not implemented yet")
