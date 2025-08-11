import os
from .base_agent import BaseAgent, AgentInput, AgentOutput

class FashionAgent(BaseAgent):
    name = "fashion_agent"
    output_schema = AgentOutput

    def run(self, input: AgentInput) -> AgentOutput:
        mode = os.getenv("LIFEMIRROR_MODE", "mock")

        if mode == "mock":
            result = AgentOutput(
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
        else:
            result = AgentOutput(success=False, data={}, error="Not implemented")

        self._trace(input.dict(), result.dict())
        return result
