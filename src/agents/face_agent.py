import os
from .base_agent import BaseAgent, AgentInput, AgentOutput

class FaceAgent(BaseAgent):
    name = "face_agent"

    def run(self, input: AgentInput) -> AgentOutput:
        mode = os.getenv("LIFEMIRROR_MODE", "mock")
        if mode == "mock":
            return AgentOutput(
                success=True,
                data={
                    "num_faces": 1,
                    "faces": [
                        {
                            "gender": "male",
                            "age_range": "20-30",
                            "expression": "smiling"
                        }
                    ]
                }
            )
        # TODO: integrate FaceTool + LLM for real reasoning
        return AgentOutput(success=False, data={}, error="Prod mode not implemented yet")
