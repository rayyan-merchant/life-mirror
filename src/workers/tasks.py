import os
from celery import Celery
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.db.models import Media
from src.agents.face_agent import FaceAgent
from src.agents.posture_agent import PostureAgent
from src.agents.fashion_agent import FashionAgent
from src.agents.detect_agent import DetectAgent
from src.agents.embed_agent import EmbedAgent
from src.utils.logging import logger

celery_app = Celery("lifemirror")
celery_app.conf.broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
celery_app.conf.result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")


def _update_media_metadata(db: Session, media_id: int, patch: dict):
    """
    Merge patch dict into media.metadata JSON.
    """
    media = db.query(Media).filter(Media.id == media_id).first()
    if not media:
        return
    metadata = media.metadata or {}
    for k, v in patch.items():
        if isinstance(v, list):
            metadata.setdefault(k, []).extend(v)
        else:
            metadata[k] = v
    media.metadata = metadata
    db.add(media)
    db.commit()


@celery_app.task
def process_media_async(media_id: int, storage_url: str):
    logger.info(f"[process_media_async] Start for media_id={media_id}, url={storage_url}")
    db = next(get_db())

    try:
        # Run agents sequentially — you can parallelize with LangGraph later
        face_res = FaceAgent().run({"media_id": media_id, "url": storage_url})
        logger.info(f"FaceAgent output: {face_res.dict()}")
        if face_res.success:
            # Store face crop URLs
            face_crops = []
            for f in face_res.data.get("faces", []):
                if f.get("crop_url"):
                    face_crops.append({
                        "crop_url": f["crop_url"],
                        "gender": f.get("gender"),
                        "age": f.get("age"),
                        "expression": f.get("expression")
                    })
            _update_media_metadata(db, media_id, {"faces": face_crops})

        posture_res = PostureAgent().run({"media_id": media_id, "url": storage_url})
        logger.info(f"PostureAgent output: {posture_res.dict()}")
        if posture_res.success:
            posture_crops = []
            crop_url = posture_res.data.get("crop_url")
            if crop_url:
                posture_crops.append({
                    "crop_url": crop_url,
                    "alignment_score": posture_res.data.get("alignment_score"),
                    "tips": posture_res.data.get("tips", [])
                })
            _update_media_metadata(db, media_id, {"posture_crops": posture_crops})

        fashion_res = FashionAgent().run({"media_id": media_id, "url": storage_url})
        logger.info(f"FashionAgent output: {fashion_res.dict()}")
        if fashion_res.success:
            fashion_crops = []
            for itm in fashion_res.data.get("items", []):
                if itm.get("crop_url"):
                    fashion_crops.append({
                        "type": itm.get("type"),
                        "score": itm.get("score"),
                        "crop_url": itm.get("crop_url")
                    })
            _update_media_metadata(db, media_id, {"fashion_crops": fashion_crops})

        detect_res = DetectAgent().run({"media_id": media_id, "url": storage_url})
        logger.info(f"DetectAgent output: {detect_res.dict()}")
        if detect_res.success:
            _update_media_metadata(db, media_id, {"objects": detect_res.data.get("detections", [])})

        embed_res = EmbedAgent().run({"media_id": media_id, "url": storage_url})
        logger.info(f"EmbedAgent output: {embed_res.dict()}")
        if embed_res.success:
            _update_media_metadata(db, media_id, {"embedding": embed_res.data.get("embedding")})

        logger.info(f"[process_media_async] Completed for media_id={media_id}")

    except Exception as e:
        logger.exception(f"process_media_async failed: {e}")
