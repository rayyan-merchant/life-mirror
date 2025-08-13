from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.agents.public_feed_agent import PublicFeedAgent

router = APIRouter()

@router.get("/feed")
def public_feed(
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    days: int = Query(None, ge=1),
    min_percentile: int = Query(None, ge=0, le=100),
    tags: list[str] = Query(None),
    search: str = Query(None),
    sort_by: str = Query("newest", regex="^(newest|highest|random|trending)$"),
    db: Session = Depends(get_db)
):
    agent = PublicFeedAgent(db)
    return {
        "items": agent.get_feed(
            limit=limit,
            offset=offset,
            days=days,
            min_percentile=min_percentile,
            tags=tags,
            search_query=search,
            sort_by=sort_by
        )
    }


@router.get("/leaderboard")
def public_leaderboard(limit: int = Query(10, le=50), db: Session = Depends(get_db)):
    agent = PublicFeedAgent(db)
    return {"items": agent.get_leaderboard(limit=limit)}


