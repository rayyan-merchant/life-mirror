from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.agents.public_feed_agent import PublicFeedAgent

router = APIRouter()

@router.get("/feed")
def public_feed(limit: int = Query(20, le=100), db: Session = Depends(get_db)):
    agent = PublicFeedAgent(db)
    return {"items": agent.get_feed(limit=limit)}

@router.get("/leaderboard")
def public_leaderboard(limit: int = Query(10, le=50), db: Session = Depends(get_db)):
    agent = PublicFeedAgent(db)
    return {"items": agent.get_leaderboard(limit=limit)}
