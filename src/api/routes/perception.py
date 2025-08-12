# src/api/routes/perception.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.services.perception import PerceptionAggregator

router = APIRouter()

@router.get("/media/{media_id}/perception")
def get_perception(media_id: int, db: Session = Depends(get_db)):
    agg = PerceptionAggregator(db)
    profile = agg.build_profile(media_id)
    if "error" in profile:
        raise HTTPException(status_code=404, detail=profile["error"])
    return profile
