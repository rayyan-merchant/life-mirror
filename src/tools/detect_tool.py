import os
from .base import BaseTool, ToolInput, ToolResult

class DetectTool(BaseTool):
    name = 'detect'

    def run(self, input: ToolInput) -> ToolResult:
        mode = os.getenv("LIFEMIRROR_MODE", "mock")
        if mode == "mock":
            return ToolResult(
                success=True,
                data={
                    "detections": [
                        {"label": "person", "score": 0.98, "bbox": [0.1, 0.1, 0.8, 0.9]},
                        {"label": "shirt", "score": 0.88, "bbox": [0.2, 0.3, 0.6, 0.5]}
                    ]
                }
            )
        # TODO: implement real object detection
        return ToolResult(success=False, data={}, error="Prod mode not implemented yet")

