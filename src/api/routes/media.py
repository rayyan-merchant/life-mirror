from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from uuid import UUID, uuid4
from src.storage.s3 import get_presigned_put_url
from src.db.session import get_db
from src.db.models import Media
from src.workers.tasks import process_media_async

router = APIRouter()

class PresignRequest(BaseModel):
    filename: str
    content_type: str
    user_id: UUID

class MediaCreateRequest(BaseModel):
    storage_url: str
    mime: str
    user_id: UUID
    metadata: dict = {}

@router.post('/presign')
async def presign(req: PresignRequest):
    # validate content_type, size limits, etc. (Guardrails/validate upstream)
    key = f"media/{req.user_id}/{req.filename}"
    presign = get_presigned_put_url(key, content_type=req.content_type)
    return {"upload_url": presign, "key": key}

@router.post('/')
async def create_media(req: MediaCreateRequest):
    # Create DB record and enqueue background processing
    media_id = uuid4()
    m = Media(id=media_id, user_id=req.user_id, storage_url=req.storage_url, mime=req.mime)
    db = next(get_db())
    db.add(m)
    db.commit()
    db.refresh(m)
    # enqueue background job
    process_media_async.delay(str(media_id), req.storage_url)
    return {"media_id": media_id}
