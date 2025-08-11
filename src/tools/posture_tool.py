# src/tools/posture_tool.py
import os
import tempfile
import math
import requests
import numpy as np
from .base import BaseTool, ToolInput, ToolResult

mp = None
cv2 = None

def _ensure_deps():
    global mp, cv2
    if mp is None:
        import mediapipe as mp_pkg
        mp = mp_pkg
    if cv2 is None:
        import cv2 as cv_pkg
        cv2 = cv_pkg

def _download_image_to_np(url_or_path: str):
    _ensure_deps()
    if url_or_path.startswith("http://") or url_or_path.startswith("https://"):
        resp = requests.get(url_or_path, timeout=20)
        resp.raise_for_status()
        arr = np.frombuffer(resp.content, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Unable to decode image")
        return img
    else:
        img = cv2.imread(url_or_path)
        if img is None:
            raise ValueError("Unable to read local image")
        return img

def _compute_alignment_score(landmarks, img_w, img_h):
    # simple heuristic: check shoulder/hip/ear vertical alignment
    # medial points indices (MediaPipe Pose): 11 (left shoulder), 12 (right shoulder)
    # 23 (left hip) 24 (right hip), 0 (nose)
    try:
        nose = landmarks[0]
        left_sh = landmarks[11]
        right_sh = landmarks[12]
        left_hip = landmarks[23]
        right_hip = landmarks[24]
        # angle between shoulders and hips center (verticality)
        sh_center_y = (left_sh[1] + right_sh[1]) / 2
        hip_center_y = (left_hip[1] + right_hip[1]) / 2
        torso_length = abs(hip_center_y - sh_center_y) + 1e-6
        # head offset from torso center
        head_offset = abs(nose[1] - sh_center_y)
        score = max(0.0, 10.0 * (1.0 - (head_offset / (torso_length + head_offset))))
        return round(score, 2)
    except Exception:
        return 5.0

class PostureTool(BaseTool):
    name = "posture"

    def run(self, input: ToolInput) -> ToolResult:
        mode = os.getenv("LIFEMIRROR_MODE", "mock")
        if mode == "mock":
            return ToolResult(success=True, data={
                "keypoints": [], "alignment_score": 8.0, "crop_url": input.url, "tips": ["Relax shoulders"]
            })

        # prod: run MediaPipe Pose
        try:
            _ensure_deps()
            import cv2 as cv
            from mediapipe import solutions as mp_solutions
            img = _download_image_to_np(input.url)
            h, w = img.shape[:2]
            img_rgb = cv.cvtColor(img, cv.COLOR_BGR2RGB)

            with mp_solutions.pose.Pose(static_image_mode=True, model_complexity=1, enable_segmentation=False) as pose:
                res = pose.process(img_rgb)
                if not res.pose_landmarks:
                    return ToolResult(success=True, data={"keypoints": [], "alignment_score": None, "crop_url": None, "tips": []})

                # convert landmarks to pixel coords list [[x,y,z], ...]
                kps = []
                for lm in res.pose_landmarks.landmark:
                    kps.append([float(lm.x * w), float(lm.y * h), float(lm.z * max(w,h))])

                # get bounding box from visible keypoints
                xs = [p[0] for p in kps]
                ys = [p[1] for p in kps]
                x_min, x_max = max(0, int(min(xs))), min(w, int(max(xs)))
                y_min, y_max = max(0, int(min(ys))), min(h, int(max(ys)))

                # enlarge box a little
                pad_x = int(0.1 * (x_max - x_min))
                pad_y = int(0.1 * (y_max - y_min))
                x0 = max(0, x_min - pad_x)
                y0 = max(0, y_min - pad_y)
                x1 = min(w, x_max + pad_x)
                y1 = min(h, y_max + pad_y)
                crop = img[y0:y1, x0:x1]

                # write crop to temp file and upload
                _, buf = cv.imencode(".jpg", crop)
                import tempfile
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                tmp.write(buf.tobytes())
                tmp.flush()
                tmp.close()

                # upload to s3
                from src.storage.s3 import upload_file
                key = f"posture/{input.media_id}/{tmp.name.split('/')[-1]}"
                crop_url = upload_file(tmp.name, key)
                try:
                    os.remove(tmp.name)
                except Exception:
                    pass

                alignment = _compute_alignment_score(kps, w, h)
                tips = []
                if alignment < 6:
                    tips = ["Straighten your back", "Relax shoulders", "Lift your chin slightly"]

                return ToolResult(success=True, data={
                    "keypoints": kps,
                    "alignment_score": alignment,
                    "crop_url": crop_url,
                    "tips": tips
                })

        except Exception as e:
            return ToolResult(success=False, data={}, error=str(e))
