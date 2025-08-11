import os
import io
import math
import tempfile
import requests
import numpy as np
import uuid
import cv2
import traceback

from .base import BaseTool, ToolInput, ToolResult
from src.storage.s3 import upload_bytes, get_presigned_get_url, S3_BUCKET

# Config
MODE = os.getenv("LIFEMIRROR_MODE", "mock")
USE_DEEPFACE = os.getenv("FACE_USE_DEEPFACE", "false").lower() in ("1", "true", "yes")
PRESIGNED_EXPIRES = int(os.getenv("S3_PRESIGNED_EXPIRES", "3600"))

# Lazy import for mediapipe to avoid import errors in mock/prod without dependency
_mp = None
_deepface = None

def _ensure_mediapipe():
    global _mp
    if _mp is None:
        import mediapipe as mp_pkg
        _mp = mp_pkg

def _ensure_deepface():
    global _deepface
    if USE_DEEPFACE and _deepface is None:
        try:
            import deepface as df_pkg
            _deepface = df_pkg
        except Exception:
            _deepface = None

def _download_image_to_np(url_or_path: str) -> np.ndarray:
    """
    Accepts a URL (http/https) or local path. Returns BGR numpy array (cv2 format).
    """
    if url_or_path.startswith("http://") or url_or_path.startswith("https://"):
        resp = requests.get(url_or_path, timeout=30)
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
    pts = []
    for lm in landmarks:
        x = lm.x * image_width
        y = lm.y * image_height
        pts.append([float(x), float(y)])
    return pts

class FaceTool(BaseTool):
    name = "face"

    def run(self, input: ToolInput) -> ToolResult:
        mode = MODE
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

        # PROD path
        try:
            _ensure_mediapipe()
            _ensure_deepface()
            mp = _mp
            mp_face = mp.solutions.face_mesh

            img = _download_image_to_np(input.url)
            h, w = img.shape[:2]
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            faces_out = []
            with mp_face.FaceMesh(static_image_mode=True,
                                  max_num_faces=5,
                                  refine_landmarks=True,
                                  min_detection_confidence=0.5) as face_mesh:
                results = face_mesh.process(img_rgb)
                if not results.multi_face_landmarks:
                    return ToolResult(success=True, data={"faces": []})

                for face_landmarks in results.multi_face_landmarks:
                    pts = _landmarks_to_xy(face_landmarks.landmark, w, h)
                    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
                    x_min, x_max = float(min(xs)), float(max(xs))
                    y_min, y_max = float(min(ys)), float(max(ys))
                    bbox_w = x_max - x_min
                    bbox_h = y_max - y_min
                    bbox = [x_min, y_min, bbox_w, bbox_h]  # xywh in pixels

                    def _get_lm(idx):
                        lm = face_landmarks.landmark[idx]
                        return [float(lm.x * w), float(lm.y * h)]

                    # sample named landmarks
                    left_eye = _get_lm(33) if len(face_landmarks.landmark) > 33 else None
                    right_eye = _get_lm(263) if len(face_landmarks.landmark) > 263 else None
                    nose_tip = _get_lm(1) if len(face_landmarks.landmark) > 1 else None
                    landmarks = {"left_eye": left_eye, "right_eye": right_eye, "nose_tip": nose_tip}

                    # crop coordinates and ensure bounds
                    x0 = max(int(math.floor(x_min)), 0)
                    y0 = max(int(math.floor(y_min)), 0)
                    x1 = min(int(math.ceil(x_max)), w)
                    y1 = min(int(math.ceil(y_max)), h)
                    if x1 <= x0 or y1 <= y0:
                        # fallback: use center small box
                        cx = int((w) / 2)
                        cy = int((h) / 2)
                        x0 = max(cx - 100, 0); y0 = max(cy - 100, 0)
                        x1 = min(cx + 100, w); y1 = min(cy + 100, h)

                    crop = img[y0:y1, x0:x1]
                    # encode to JPEG bytes
                    ok, buf = cv2.imencode(".jpg", crop, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
                    if not ok:
                        raise RuntimeError("Failed to encode face crop")

                    jpeg_bytes = buf.tobytes()

                    # Upload to S3 and create presigned GET URL
                    key = f"faces/{input.media_id}/{uuid.uuid4().hex}.jpg"
                    upload_bytes(jpeg_bytes, key, content_type="image/jpeg")
                    presigned = get_presigned_get_url(key, expires_in=PRESIGNED_EXPIRES)

                    attributes = {"gender": None, "age": None, "expression": None}
                    # optional attribute estimation (deepface)
                    if USE_DEEPFACE and _deepface is not None:
                        try:
                            # deepface expects file path or np array in RGB
                            crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
                            # DeepFace.analyze supports np array with enforce_detection=False
                            analysis = _deepface.DeepFace.analyze(img_path=crop_rgb, actions=['age', 'gender', 'emotion'], enforce_detection=False)
                            attributes["age"] = int(analysis.get("age")) if analysis.get("age") else None
                            attributes["gender"] = analysis.get("gender")
                            emotion = analysis.get("emotion")
                            if isinstance(emotion, dict) and len(emotion) > 0:
                                top_emotion = max(emotion.items(), key=lambda x: x[1])[0]
                                attributes["expression"] = top_emotion
                        except Exception:
                            # do not fail whole pipeline for attribute extraction
                            pass

                    faces_out.append({
                        "bbox": [float(b) for b in bbox],
                        "landmarks": landmarks,
                        "crop_url": presigned,   # presigned GET URL (valid for S3_PRESIGNED_EXPIRES seconds)
                        "attributes": attributes
                    })

            return ToolResult(success=True, data={"faces": faces_out})

        except Exception as e:
            # include traceback for easier debugging (will be logged)
            tb = traceback.format_exc()
            return ToolResult(success=False, data={}, error=f"{str(e)}\n{tb}")
