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

        # --- PROD MODE ---
        try:
            from ultralytics import YOLO
            model = YOLO("yolov8n.pt")  # small model for speed, can switch to yolov8m/l
            results = model(input.url)  # URL or local file path
            detections = []
            for r in results:
                for box in r.boxes:
                    cls_name = r.names[int(box.cls[0])]
                    score = float(box.conf[0])
                    xywh = box.xywh[0].tolist()  # [x_center, y_center, width, height]
                    detections.append({"label": cls_name, "score": score, "bbox": xywh})
            return ToolResult(success=True, data={"detections": detections})

        except Exception as e:
            return ToolResult(success=False, data={}, error=str(e))
