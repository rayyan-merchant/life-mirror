from src.db.session import get_db
from src.db.models import Embedding, Face, Detection
import uuid

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
