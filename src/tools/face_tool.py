import os
import io
import math
import tempfile
import requests
import numpy as np

from .base import BaseTool, ToolInput, ToolResult

MODE = os.getenv("LIFEMIRROR_MODE", "mock")
USE_DEEPFACE = os.getenv("FACE_USE_DEEPFACE", "false").lower() in ("1", "true", "yes")

# Lazy imports for optional libs
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
    """
    Accepts a URL (http/https) or local path. Returns BGR numpy array (cv2 format).
    """
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
    pts = []
    for lm in landmarks:
        x = lm.x * image_width
        y = lm.y * image_height
        pts.append([float(x), float(y)])
    return pts


class FaceTool(BaseTool):
    name = "face"

    def run(self, input: ToolInput) -> ToolResult:
        mode = os.getenv("LIFEMIRROR_MODE", "mock")
        if mode == "mock":
            # deterministic mock as before
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

        # PROD PATH using MediaPipe
        try:
            _ensure_deps()
            # initialize face mesh
            mp_face = mp.solutions.face_mesh
            img = _download_image_to_np(input.url)
            h, w = img.shape[:2]

            # convert BGR->RGB for mediapipe
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            with mp_face.FaceMesh(static_image_mode=True,
                                  max_num_faces=5,
                                  refine_landmarks=True,
                                  min_detection_confidence=0.5) as face_mesh:
                results = face_mesh.process(img_rgb)
                faces_out = []
                if not results.multi_face_landmarks:
                    return ToolResult(success=True, data={"faces": []})

                for face_idx, face_landmarks in enumerate(results.multi_face_landmarks):
                    # compute bounding box from landmarks
                    pts = _landmarks_to_xy(face_landmarks.landmark, w, h)
                    xs = [p[0] for p in pts]
                    ys = [p[1] for p in pts]
                    x_min, x_max = float(min(xs)), float(max(xs))
                    y_min, y_max = float(min(ys)), float(max(ys))
                    bbox_w = x_max - x_min
                    bbox_h = y_max - y_min
                    bbox = [x_min, y_min, bbox_w, bbox_h]  # xywh in pixels

                    # sample some named landmarks (left/right eye, nose tip)
                    def _get_lm(idx):
                        lm = face_landmarks.landmark[idx]
                        return [float(lm.x * w), float(lm.y * h)]
                    # MediaPipe face mesh indices: 33 left eye outer, 263 right eye outer, 1 nose tip
                    left_eye = _get_lm(33)
                    right_eye = _get_lm(263)
                    nose_tip = _get_lm(1)

                    landmarks = {
                        "left_eye": left_eye,
                        "right_eye": right_eye,
                        "nose_tip": nose_tip,
                        # you can add more if desired
                    }

                    # create crop (optional) - save to a temp file and return path (or upload to S3 in prod)
                    x0 = max(int(math.floor(x_min)), 0)
                    y0 = max(int(math.floor(y_min)), 0)
                    x1 = min(int(math.ceil(x_max)), w)
                    y1 = min(int(math.ceil(y_max)), h)
                    crop = img[y0:y1, x0:x1]
                    # Write crop to temp file and return a file:// path, you can replace with S3 upload
                    _, buf = cv2.imencode(".jpg", crop)
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                    tmp.write(buf.tobytes())
                    tmp.flush()
                    crop_path = tmp.name
                    tmp.close()

                    attributes = {"gender": None, "age": None, "expression": None}

                    # optional attribute estimation using deepface
                    if USE_DEEPFACE and deepface is not None:
                        try:
                            # deepface expects RGB
                            crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
                            # DeepFace.analyze returns dict with age, gender, emotion keys
                            analysis = deepface.DeepFace.analyze(img_path=crop_rgb, actions=['age', 'gender', 'emotion'], enforce_detection=False)
                            attributes["age"] = int(analysis.get("age")) if analysis.get("age") else None
                            attributes["gender"] = analysis.get("gender")
                            emotion = analysis.get("emotion")
                            if isinstance(emotion, dict):
                                # pick highest emotion
                                top_emotion = max(emotion.items(), key=lambda x: x[1])[0]
                                attributes["expression"] = top_emotion
                        except Exception:
                            # don't fail pipeline on attribute extraction errors
                            pass

                    faces_out.append({
                        "bbox": [float(b) for b in bbox],
                        "landmarks": landmarks,
                        "crop_path": crop_path,   # local path — you should upload to S3 in prod and replace with URL
                        "attributes": attributes
                    })

                return ToolResult(success=True, data={"faces": faces_out})

        except Exception as e:
            return ToolResult(success=False, data={}, error=str(e))
