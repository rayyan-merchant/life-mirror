import os
from .base_agent import BaseAgent, AgentInput, AgentOutput
from src.tools.base import ToolInput
from src.tools.face_tool import FaceTool

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
            self._trace(input.dict(), result.dict())
            return result

        # Prod: call FaceTool
        tool_input = ToolInput(media_id=input.media_id, url=input.url)
        tool_res = FaceTool().run(tool_input)
        if not tool_res.success:
            result = AgentOutput(success=False, data={}, error=tool_res.error)
            self._trace(input.dict(), result.dict())
            return result

        faces = []
        for f in tool_res.data.get("faces", []):
            attrs = f.get("attributes", {}) or {}
            # convert age to range if present
            age = attrs.get("age")
            age_range = None
            if isinstance(age, (int, float)):
                a = int(age)
                age_range = f"{max(0, a-5)}-{a+5}"
            faces.append({
                "bbox": f.get("bbox"),
                "landmarks": f.get("landmarks"),
                "crop_path": f.get("crop_path"),
                "gender": attrs.get("gender"),
                "age": attrs.get("age"),
                "age_range": age_range,
                "expression": attrs.get("expression")
            })

        result = AgentOutput(success=True, data={"num_faces": len(faces), "faces": faces})
        self._trace(input.dict(), result.dict())
        return result
