# src/agents/fashion_agent.py
import os
import tempfile
import requests
import numpy as np
import cv2
from .base_agent import BaseAgent, AgentInput, AgentOutput
from src.tools.detect_tool import DetectTool
from src.tools.base import ToolInput
from src.storage.s3 import upload_file
from sklearn.cluster import KMeans


# default fashion classes (can be extended)
DEFAULT_FASHION_CLASSES = {
    "shirt", "t-shirt", "jeans", "pants", "dress", "jacket", "coat",
    "bag", "handbag", "backpack", "hat", "cap", "shoe", "shoes", "tie",
    "skirt", "shorts", "sneakers", "sandal"
}

def _rgb_to_hex(rgb):
    # rgb: (B, G, R) or (R,G,B) depending on source; we use cv2 which uses BGR
    # convert to int and produce hex string
    r = int(rgb[2]) if len(rgb) == 3 else int(rgb[0])
    g = int(rgb[1]) if len(rgb) == 3 else int(rgb[1])
    b = int(rgb[0]) if len(rgb) == 3 else int(rgb[2])
    return "#{:02x}{:02x}{:02x}".format(r, g, b)


def _dominant_color_hex(crop_bgr):
    """
    Extract dominant color via K-Means (k=3) from the given BGR crop.
    Returns HEX string.
    """
    try:
        # Resize for speed
        small_img = cv2.resize(crop_bgr, (50, 50), interpolation=cv2.INTER_AREA)
        # Reshape to (num_pixels, 3)
        pixels = small_img.reshape((-1, 3))
        # Fit KMeans to find clusters
        clt = KMeans(n_clusters=3, random_state=42, n_init=10)
        clt.fit(pixels)
        # Find the cluster with the largest number of pixels
        labels, counts = np.unique(clt.labels_, return_counts=True)
        dominant_cluster_idx = labels[np.argmax(counts)]
        dominant_color_bgr = clt.cluster_centers_[dominant_cluster_idx]
        return _rgb_to_hex(dominant_color_bgr)  # _rgb_to_hex already expects BGR
    except Exception:
        return None


class FashionAgent(BaseAgent):
    name = "fashion_agent"
    output_schema = AgentOutput

    def run(self, input: AgentInput) -> AgentOutput:
        """
        - In mock mode returns deterministic example.
        - In prod: runs DetectTool, crops fashion item regions, uploads to S3, returns metadata.
        """
        mode = os.getenv("LIFEMIRROR_MODE", "mock")
        fashion_classes_env = os.getenv("FASHION_CLASSES")
        if fashion_classes_env:
            fashion_classes = set([c.strip().lower() for c in fashion_classes_env.split(",") if c.strip()])
        else:
            fashion_classes = DEFAULT_FASHION_CLASSES

        # Mock mode: same as before
        if mode == "mock":
            result = AgentOutput(success=True, data={
                "style": "casual",
                "items": [
                    {"type": "shirt", "score": 0.95, "bbox": [0.2,0.2,0.4,0.5], "crop_url": input.url, "dominant_color": "#6fa3ff"}
                ],
                "overall_rating": 7.5
            })
            self._trace(input.dict(), result.dict())
            return result

        # Prod mode: call DetectTool
        tool_in = ToolInput(media_id=input.media_id, url=input.url)
        det_res = DetectTool().run(tool_in)
        if not det_res.success:
            out = AgentOutput(success=False, data={}, error=det_res.error)
            self._trace(input.dict(), out.dict())
            return out

        detections = det_res.data.get("detections", [])
        if not detections:
            out = AgentOutput(success=True, data={"style": "unknown", "items": [], "overall_rating": 0})
            self._trace(input.dict(), out.dict())
            return out

        # download full image once
        try:
            resp = requests.get(input.url, timeout=20)
            resp.raise_for_status()
            arr = np.frombuffer(resp.content, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Failed to decode image")
        except Exception as e:
            out = AgentOutput(success=False, data={}, error=f"image download error: {e}")
            self._trace(input.dict(), out.dict())
            return out

        h, w = img.shape[:2]
        items = []

        for d in detections:
            label = str(d.get("label", "")).lower()
            if label not in fashion_classes:
                continue

            bbox = d.get("bbox", [])
            # Support two bbox formats:
            # - normalized center xy + wh (0..1): [x_center, y_center, w_norm, h_norm]
            # - pixel center xy + wh: [x_center_px, y_center_px, w_px, h_px]
            # - optionally xyxy (x0,y0,x1,y1)
            try:
                if len(bbox) == 4:
                    x, y, bw, bh = bbox
                    # If bw and bh are <= 1, treat as normalized center coords
                    if bw <= 1 and bh <= 1:
                        cx = x * w
                        cy = y * h
                        pw = bw * w
                        ph = bh * h
                        x0 = int(cx - pw / 2)
                        y0 = int(cy - ph / 2)
                        x1 = int(cx + pw / 2)
                        y1 = int(cy + ph / 2)
                    else:
                        # treat x,y as center in px
                        cx = x
                        cy = y
                        pw = bw
                        ph = bh
                        x0 = int(cx - pw / 2)
                        y0 = int(cy - ph / 2)
                        x1 = int(cx + pw / 2)
                        y1 = int(cy + ph / 2)
                elif len(bbox) == 2:
                    # maybe (x0,y0) single point - skip
                    continue
                elif len(bbox) == 5:
                    # some detectors output xyxy + conf; attempt best-effort parse
                    x0, y0, x1, y1, _ = bbox
                    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
                else:
                    continue
            except Exception:
                continue

            # Clip coords
            x0, y0 = max(0, x0), max(0, y0)
            x1, y1 = min(w, x1), min(h, y1)
            if x1 <= x0 or y1 <= y0:
                continue

            crop = img[y0:y1, x0:x1]
            if crop.size == 0:
                continue

            # encode crop to JPG
            try:
                ok, buf = cv2.imencode(".jpg", crop)
                if not ok:
                    continue
            except Exception:
                continue

            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            try:
                tmp.write(buf.tobytes())
                tmp.flush()
                tmp.close()
                key = f"fashion/{input.media_id}/{os.path.basename(tmp.name)}"
                try:
                    crop_url = upload_file(tmp.name, key)
                except Exception:
                    # fallback: keep original image url if upload fails
                    crop_url = input.url
                finally:
                    try:
                        os.remove(tmp.name)
                    except Exception:
                        pass
            except Exception:
                try:
                    tmp.close()
                except Exception:
                    pass
                try:
                    os.remove(tmp.name)
                except Exception:
                    pass
                continue

            dominant_color = _dominant_color_hex(crop)

            items.append({
                "type": label,
                "score": float(d.get("score", 0.0)),
                "bbox": [x0, y0, x1, y1],
                "crop_url": crop_url,
                "dominant_color": dominant_color
            })

        # Simple style heuristics — you can replace with LLM later
        style = "unknown"
        if any(it["type"] in ("dress", "jacket", "coat") for it in items):
            style = "formal"
        elif any(it["type"] in ("shirt", "jeans", "sneakers", "shorts") for it in items):
            style = "casual"

        overall_rating = round(min(10.0, 5.0 + 0.5 * len(items)), 1)  # toy heuristic

        result = AgentOutput(success=True, data={"style": style, "items": items, "overall_rating": overall_rating})
        self._trace(input.dict(), result.dict())
        return result
