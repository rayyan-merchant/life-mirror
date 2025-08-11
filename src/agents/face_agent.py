import os
from .base_agent import BaseAgent, AgentInput, AgentOutput

class FaceAgent(BaseAgent):
    name = "face_agent"
    output_schema = AgentOutput

    def run(self, input: AgentInput) -> AgentOutput:
        mode = os.getenv("LIFEMIRROR_MODE", "mock")

        if mode == "mock":
            result = AgentOutput(
                success=True,
                data={
                    "num_faces": 1,
                    "faces": [
                        {"gender": "male", "age_range": "20-30", "expression": "smiling"}
                    ]
                }
            )
        else:
            result = AgentOutput(success=False, data={}, error="Not implemented")

        self._trace(input.dict(), result.dict())
        return result
