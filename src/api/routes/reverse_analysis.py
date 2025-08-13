from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from src.agents.reverse_analysis_agent import ReverseAnalysisAgent, AgentInput
from src.db.session import get_db
from src.db.models import Media
from src.workers.tasks import _update_media_metadata

router = APIRouter()

@router.get("/reverse-analysis")
def reverse_analysis(
    user_id: int = Query(..., description="ID of the user"),
    goal: str = Query(..., description="Desired perception/vibe"),
    recent_limit: int = Query(5, description="Number of recent uploads to consider")
):
    agent = ReverseAnalysisAgent()
    res = agent.run(AgentInput(
        media_id=0,
        url=None,
        data={
            "user_id": user_id,
            "goal": goal,
            "recent_limit": recent_limit
        }
    ))

    if not res.success:
        raise HTTPException(status_code=400, detail=res.error)

    # Store result in metadata of latest media
    db = next(get_db())
    latest_media = (
        db.query(Media)
        .filter(Media.user_id == user_id)
        .order_by(Media.created_at.desc())
        .first()
    )
    if latest_media:
        _update_media_metadata(db, latest_media.id, {"reverse_analysis": res.data})

    return res.data
