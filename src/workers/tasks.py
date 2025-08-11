from src.db.session import get_db
from src.db.models import Embedding, Face, Detection
import uuid
from src.db.models import Media
import json

def _update_media_metadata(db, media_id, patch: dict):
    media = db.query(Media).filter(Media.id == media_id).first()
    if not media:
        return
    metadata = media.metadata or {}
    # merge arrays
    for k, v in patch.items():
        if isinstance(v, list):
            metadata.setdefault(k, []).extend(v)
        else:
            metadata[k] = v
    media.metadata = metadata
    db.add(media)
    db.commit()

# Example usage in the task after running agents/tools:
# suppose fashion_out is the AgentOutput dict from FashionAgent:
fashion_out = fashion_data  # agent output dict
# extract crop urls list
fashion_crops = []
for itm in fashion_out.get("data", {}).get("items", []):
    if itm.get("crop_url"):
        fashion_crops.append({"type": itm.get("type"), "crop_url": itm.get("crop_url")})

_update_media_metadata(db, media_id, {"fashion_crops": fashion_crops})

# posture_out similarly:
posture_out = posture_data
posture_crops = []
if posture_out.get("data", {}).get("crop_url"):
    posture_crops.append({"crop_url": posture_out["data"]["crop_url"], "alignment_score": posture_out["data"].get("alignment_score")})
_update_media_metadata(db, media_id, {"posture_crops": posture_crops})


@celery.task(name='src.workers.tasks.process_media')
def process_media_async(media_id: str, storage_url: str):
    db = next(get_db())

    tool_input = ToolInput(media_id=media_id, url=storage_url)

    # Embedding
    embed_res = EmbedTool().run(tool_input)
    if embed_res.success:
        db.add(Embedding(id=uuid.uuid4(), media_id=media_id,
                         vector=embed_res.data["vector"],
                         model=embed_res.data["model"]))

    # Face detection
    face_res = FaceTool().run(tool_input)
    if face_res.success:
        for f in face_res.data["faces"]:
            db.add(Face(id=uuid.uuid4(), media_id=media_id,
                        bbox=f["bbox"], landmarks=f.get("landmarks"),
                        crop_url=f.get("crop_url")))

    # Object detection
    detect_res = DetectTool().run(tool_input)
    if detect_res.success:
        for d in detect_res.data["detections"]:
            db.add(Detection(id=uuid.uuid4(), media_id=media_id,
                             label=d["label"], score=d["score"], bbox=d["bbox"]))

    db.commit()
