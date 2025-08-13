from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from src.agents.fixit_agent import FixitAgent, AgentInput
from src.agents.reverse_analysis_agent import ReverseAnalysisAgent
from src.db.session import get_db
from src.db.models import Media
from src.workers.tasks import _update_media_metadata

router = APIRouter()

@router.get("/fixit-suggestions")
def get_fixit_suggestions(
    user_id: int = Query(..., description="ID of the user"),
    media_id: Optional[int] = Query(None, description="Latest media ID to base suggestions on"),
    recent_limit: int = Query(5, description="Number of recent uploads to consider"),
    with_reverse_analysis: bool = Query(False, description="If true, also run Reverse Analysis")
):
    """
    Generate improvement suggestions based on recent perception data and history trends.
    Optionally run Reverse Analysis right after Fix-it.
    """
    # --- Run Fix-it Agent ---
    fixit_agent = FixitAgent()
    fixit_res = fixit_agent.run(AgentInput(
        media_id=media_id or 0,
        url=None,
        data={
            "user_id": user_id,
            "media_id": media_id or 0,
            "recent_limit": recent_limit
        }
    ))

    if not fixit_res.success:
        raise HTTPException(status_code=400, detail=fixit_res.error)

    db = next(get_db())

    # Store Fix-it results
    latest_media = (
        db.query(Media)
        .filter(Media.user_id == user_id)
        .order_by(Media.created_at.desc())
        .first()
    )
    if latest_media:
        _update_media_metadata(db, latest_media.id, {"fixit_suggestions": fixit_res.data})

    # --- Optionally run Reverse Analysis ---
    reverse_res = None
    if with_reverse_analysis:
        # You can choose to auto-fill a default goal from Fix-it's focus_areas
        default_goal = f"Improve in areas: {', '.join(fixit_res.data.get('focus_areas', []))}"
        reverse_agent = ReverseAnalysisAgent()
        reverse_res = reverse_agent.run(AgentInput(
            media_id=0,
            url=None,
            data={
                "user_id": user_id,
                "goal": default_goal,
                "recent_limit": recent_limit
            }
        ))

        if reverse_res.success and latest_media:
            _update_media_metadata(db, latest_media.id, {"reverse_analysis": reverse_res.data})

    return {
        "fixit_suggestions": fixit_res.data,
        "reverse_analysis": reverse_res.data if reverse_res and reverse_res.success else None
    }
