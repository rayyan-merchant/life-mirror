import os
from .base_agent import BaseAgent, AgentInput, AgentOutput

class FashionAgent(BaseAgent):
    name = "fashion_agent"

    def run(self, input: AgentInput) -> AgentOutput:
        mode = os.getenv("LIFEMIRROR_MODE", "mock")
        if mode == "mock":
            return AgentOutput(
                success=True,
                data={
                    "style": "casual",
                    "items": [
                        {"type": "shirt", "color": "blue"},
                        {"type": "jeans", "color": "black"}
                    ],
                    "overall_rating": 7.5
                }
            )
        # TODO: integrate DetectTool + LLM analysis
        return AgentOutput(success=False, data={}, error="Prod mode not implemented yet")
