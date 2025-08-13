from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from src.agents.fixit_agent import FixitAgent, AgentInput
from src.agents.reverse_analysis_agent import ReverseAnalysisAgent
from src.agents.vibe_analysis_agent import VibeAnalysisAgent
from src.db.session import get_db
from src.db.models import Media
from src.workers.tasks import _update_media_metadata

router = APIRouter()

@router.post("/full-analysis")
def full_analysis(
    user_id: int = Query(..., description="ID of the user"),
    goal: Optional[str] = Query(None, description="Goal for Reverse Analysis. If not provided, auto-generated from Fix-it."),
    recent_limit: int = Query(5, description="Number of recent uploads to consider")
):
    """
    Runs Fix-it → Reverse Analysis → Vibe Analysis in sequence.
    Stores all results in latest media metadata.
    """

    db = next(get_db())
    latest_media = (
        db.query(Media)
        .filter(Media.user_id == user_id)
        .order_by(Media.created_at.desc())
        .first()
    )
    if not latest_media:
        raise HTTPException(status_code=404, detail="No media found for this user.")

    # --- Step 1: Fix-it ---
    fixit_agent = FixitAgent()
    fixit_res = fixit_agent.run(AgentInput(
        media_id=latest_media.id,
        url=None,
        data={"user_id": user_id, "media_id": latest_media.id, "recent_limit": recent_limit}
    ))
    if not fixit_res.success:
        raise HTTPException(status_code=400, detail=f"Fix-it failed: {fixit_res.error}")
    _update_media_metadata(db, latest_media.id, {"fixit_suggestions": fixit_res.data})

    # --- Step 2: Reverse Analysis ---
    final_goal = goal or f"Improve in areas: {', '.join(fixit_res.data.get('focus_areas', []))}"
    reverse_agent = ReverseAnalysisAgent()
    reverse_res = reverse_agent.run(AgentInput(
        media_id=0,
        url=None,
        data={"user_id": user_id, "goal": final_goal, "recent_limit": recent_limit}
    ))
    if not reverse_res.success:
        raise HTTPException(status_code=400, detail=f"Reverse Analysis failed: {reverse_res.error}")
    _update_media_metadata(db, latest_media.id, {"reverse_analysis": reverse_res.data})

    # --- Step 3: Vibe Analysis ---
    vibe_agent = VibeAnalysisAgent()
    vibe_res = vibe_agent.run(AgentInput(
        media_id=0,
        url=None,
        data={"user_id": user_id, "recent_limit": recent_limit}
    ))
    if not vibe_res.success:
        raise HTTPException(status_code=400, detail=f"Vibe Analysis failed: {vibe_res.error}")
    _update_media_metadata(db, latest_media.id, {"vibe_analysis": vibe_res.data})

    return {
        "fixit_suggestions": fixit_res.data,
        "reverse_analysis": reverse_res.data,
        "vibe_analysis": vibe_res.data
    }
