class FaceAgent(BaseAgent):
    name = "face_agent"
    output_schema = AgentOutput

    def run(self, input: AgentInput) -> AgentOutput:
        from src.tools.face_tool import FaceTool, ToolInput

        tool_res = FaceTool().run(ToolInput(media_id=input.media_id, url=input.url))
        if not tool_res.success:
            result = AgentOutput(success=False, data={}, error=tool_res.error)
            self._trace(input.dict(), result.dict())
            return result

        faces = []
        for f in tool_res.data.get("faces", []):
            attrs = f.get("attributes", {}) or {}
            age_range = None
            if isinstance(attrs.get("age"), (int, float)):
                a = int(attrs["age"])
                age_range = f"{max(0, a-5)}-{a+5}"
            faces.append({
                "bbox": f.get("bbox"),
                "landmarks": f.get("landmarks"),
                "crop_url": f.get("crop_url"),
                "gender": attrs.get("gender"),
                "age": attrs.get("age"),
                "age_range": age_range,
                "expression": attrs.get("expression")
            })

        result = AgentOutput(success=True, data={"num_faces": len(faces), "faces": faces})
        self._trace(input.dict(), result.dict())
        return result
