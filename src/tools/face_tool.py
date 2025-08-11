import os
import math
import tempfile
import requests
import numpy as np
from .base import BaseTool, ToolInput, ToolResult

MODE = os.getenv("LIFEMIRROR_MODE", "mock")
USE_DEEPFACE = os.getenv("FACE_USE_DEEPFACE", "false").lower() in ("1", "true", "yes")

mp = None
cv2 = None
deepface = None

def _ensure_deps():
    global mp, cv2, deepface
    if mp is None:
        import mediapipe as mp_pkg
        mp = mp_pkg
    if cv2 is None:
        import cv2 as cv_pkg
        cv2 = cv_pkg
    if USE_DEEPFACE and deepface is None:
        try:
            import deepface as df_pkg
            deepface = df_pkg
        except Exception:
            deepface = None

def _download_image_to_np(url_or_path: str) -> np.ndarray:
    _ensure_deps()
    if url_or_path.startswith("http://") or url_or_path.startswith("https://"):
        resp = requests.get(url_or_path, timeout=20)
        resp.raise_for_status()
        arr = np.frombuffer(resp.content, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Unable to decode image from url")
        return img
    else:
        img = cv2.imread(url_or_path)
        if img is None:
            raise ValueError("Unable to read local image path")
        return img

def _landmarks_to_xy(landmarks, image_width, image_height):
    return [[float(lm.x * image_width), float(lm.y * image_height)] for lm in landmarks]

class FaceTool(BaseTool):
    name = "face"

    def run(self, input: ToolInput) -> ToolResult:
        from src.storage.s3 import upload_file  # your existing S3 uploader

        mode = os.getenv("LIFEMIRROR_MODE", "mock")
        if mode == "mock":
            return ToolResult(
                success=True,
                data={
                    "faces": [
                        {
                            "bbox": [100, 50, 80, 80],
                            "landmarks": {"left_eye": [110, 70], "right_eye": [150, 70]},
                            "crop_url": input.url,
                            "attributes": {"gender": None, "age": None, "expression": None}
                        }
                    ]
                }
            )

        try:
            _ensure_deps()
            mp_face = mp.solutions.face_mesh
            img = _download_image_to_np(input.url)
            h, w = img.shape[:2]
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            with mp_face.FaceMesh(static_image_mode=True,
                                  max_num_faces=5,
                                  refine_landmarks=True,
                                  min_detection_confidence=0.5) as face_mesh:
                results = face_mesh.process(img_rgb)
                faces_out = []
                if not results.multi_face_landmarks:
                    return ToolResult(success=True, data={"faces": []})

                for face_landmarks in results.multi_face_landmarks:
                    pts = _landmarks_to_xy(face_landmarks.landmark, w, h)
                    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
                    x_min, x_max = float(min(xs)), float(max(xs))
                    y_min, y_max = float(min(ys)), float(max(ys))
                    bbox = [x_min, y_min, x_max - x_min, y_max - y_min]

                    def _get_lm(idx):
                        lm = face_landmarks.landmark[idx]
                        return [float(lm.x * w), float(lm.y * h)]
                    landmarks = {
                        "left_eye": _get_lm(33),
                        "right_eye": _get_lm(263),
                        "nose_tip": _get_lm(1),
                    }

                    # Crop image
                    x0, y0 = max(int(x_min), 0), max(int(y_min), 0)
                    x1, y1 = min(int(x_max), w), min(int(y_max), h)
                    crop = img[y0:y1, x0:x1]
                    _, buf = cv2.imencode(".jpg", crop)
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                        tmp.write(buf.tobytes())
                        tmp.flush()
                        crop_url = upload_file(tmp.name, f"faces/{os.path.basename(tmp.name)}")

                    attributes = {"gender": None, "age": None, "expression": None}
                    if USE_DEEPFACE and deepface is not None:
                        try:
                            crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
                            analysis = deepface.DeepFace.analyze(
                                img_path=crop_rgb,
                                actions=['age', 'gender', 'emotion'],
                                enforce_detection=False
                            )
                            attributes["age"] = int(analysis.get("age")) if analysis.get("age") else None
                            attributes["gender"] = analysis.get("gender")
                            if isinstance(analysis.get("emotion"), dict):
                                top_emotion = max(analysis["emotion"].items(), key=lambda x: x[1])[0]
                                attributes["expression"] = top_emotion
                        except Exception:
                            pass

                    faces_out.append({
                        "bbox": bbox,
                        "landmarks": landmarks,
                        "crop_url": crop_url,
                        "attributes": attributes
                    })

                return ToolResult(success=True, data={"faces": faces_out})

        except Exception as e:
            return ToolResult(success=False, data={}, error=str(e))
