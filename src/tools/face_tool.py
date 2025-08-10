import os
from .base import BaseTool, ToolInput, ToolResult

class FaceTool(BaseTool):
    name = 'face'

    def run(self, input: ToolInput) -> ToolResult:
        mode = os.getenv("LIFEMIRROR_MODE", "mock")
        if mode == "mock":
            return ToolResult(
                success=True,
                data={
                    "faces": [
                        {
                            "bbox": [100, 50, 80, 80],
                            "landmarks": {"left_eye": [110, 70], "right_eye": [150, 70]},
                            "crop_url": input.url
                        }
                    ]
                }
            )
        # TODO: implement real face detection here
        return ToolResult(success=False, data={}, error="Prod mode not implemented yet")

