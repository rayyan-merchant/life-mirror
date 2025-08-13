import os
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
from uuid import UUID, uuid4
from src.storage.s3 import get_presigned_put_url
from src.db.session import get_db
from src.db.models import Media
from src.workers.tasks import process_media_async
from src.core.rate_limit import rl_upload
from starlette.status import HTTP_413_REQUEST_ENTITY_TOO_LARGE

router = APIRouter()

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))
ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp", "video/mp4", "video/quicktime"}

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


@router.post("/upload", dependencies=[Depends(rl_upload())])
async def upload_media(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(status_code=415, detail="Unsupported media type")

    # Size guard (works when client sends Content-Length or via stream read)
    content_length = file.spool_max_size if hasattr(file, "spool_max_size") else None
    # Fallback: read stream in chunks to enforce cap
    size = 0
    chunk = await file.read(1024 * 1024)
    data = b""
    while chunk:
        size += len(chunk)
        if size > MAX_UPLOAD_MB * 1024 * 1024:
            raise HTTPException(status_code=HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")
        data += chunk
        chunk = await file.read(1024 * 1024)
    await file.close()

    # ... store `data` to your storage service (S3/R2) and enqueue processing ...
    # return {"status": "ok", "storage_url": ..., "media_id": ...}

