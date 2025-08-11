# src/agents/fashion_agent.py
import os
from .base_agent import BaseAgent, AgentInput, AgentOutput
from src.tools.detect_tool import DetectTool
from src.tools.base import ToolInput
import numpy as np
import requests
import cv2
import tempfile
from src.storage.s3 import upload_file

FASHION_CLASSES = {"shirt", "pants", "shoe", "shoes", "dress", "jacket", "coat", "bag", "hat", "tie"}

class FashionAgent(BaseAgent):
    name = "fashion_agent"
    output_schema = AgentOutput

    def run(self, input: AgentInput) -> AgentOutput:
        mode = os.getenv("LIFEMIRROR_MODE", "mock")
        if mode == "mock":
            result = AgentOutput(success=True, data={
                "style": "casual",
                "items": [{"type":"shirt","color":"blue","crop_url": input.url}],
                "overall_rating": 7.5
            })
            self._trace(input.dict(), result.dict())
            return result

        # Prod: call DetectTool
        tool_in = ToolInput(media_id=input.media_id, url=input.url)
        det_res = DetectTool().run(tool_in)
        if not det_res.success:
            out = AgentOutput(success=False, data={}, error=det_res.error)
            self._trace(input.dict(), out.dict())
            return out

        detections = det_res.data.get("detections", [])
        # download image once
        try:
            resp = requests.get(input.url, timeout=20)
            resp.raise_for_status()
            arr = np.frombuffer(resp.content, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        except Exception as e:
            out = AgentOutput(success=False, data={}, error=f"download error: {e}")
            self._trace(input.dict(), out.dict())
            return out

        h, w = img.shape[:2]
        items = []
        for d in detections:
            label = d.get("label", "").lower()
            if label not in FASHION_CLASSES:
                continue
            bbox = d.get("bbox", [])  # assume xywh normalized (0..1) or pixel; we'll handle both
            # DetectTool in prod returns xywh in pixels; if normalized (<1) then convert
            if len(bbox) == 4:
                x, y, bw, bh = bbox
                if bw <= 1 and bh <= 1:  # normalized coords
                    x0 = int(x * w - (bw * w) / 2)
                    y0 = int(y * h - (bh * h) / 2)
                    x1 = int(x0 + bw * w)
                    y1 = int(y0 + bh * h)
                else:
                    # treat as pixels centered
                    x0 = int(x - bw/2)
                    y0 = int(y - bh/2)
                    x1 = int(x + bw/2)
                    y1 = int(y + bh/2)
                x0, y0 = max(0, x0), max(0, y0)
                x1, y1 = min(w, x1), min(h, y1)
            else:
                continue

            crop = img[y0:y1, x0:x1]
            if crop.size == 0:
                continue
            _, buf = cv2.imencode(".jpg", crop)
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            tmp.write(buf.tobytes())
            tmp.flush()
            tmp.close()
            key = f"fashion/{input.media_id}/{tmp.name.split('/')[-1]}"
            try:
                crop_url = upload_file(tmp.name, key)
            except Exception:
                crop_url = input.url
            try:
                os.remove(tmp.name)
            except Exception:
                pass

            items.append({
                "type": label,
                "score": float(d.get("score", 0)),
                "bbox": bbox,
                "crop_url": crop_url
            })

        # simple style aggregation
        style = "unknown"
        if any(i["type"] in ("shirt","jeans","dress","jacket") for i in items):
            style = "casual"

        result = AgentOutput(success=True, data={"style": style, "items": items, "overall_rating": 6.5})
        self._trace(input.dict(), result.dict())
        return result
