import uuid
from fastapi import APIRouter, Query, HTTPException
from src.services.storage import generate_upload_url, generate_download_url

router = APIRouter()

@router.get("/upload-url")
def get_upload_url(content_type: str = Query(...)):
    key = f"uploads/{uuid.uuid4()}"
    url = generate_upload_url(key, content_type)
    return {"upload_url": url, "storage_key": key}

@router.get("/download-url")
def get_download_url(storage_key: str = Query(...)):
    url = generate_download_url(storage_key)
    return {"download_url": url}
