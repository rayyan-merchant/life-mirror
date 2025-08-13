from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from src.agents.fixit_agent import FixitAgent, AgentInput

router = APIRouter()

@router.get("/fixit-suggestions")
def get_fixit_suggestions(
    user_id: int = Query(..., description="ID of the user"),
    media_id: Optional[int] = Query(None, description="Latest media ID to base suggestions on"),
    recent_limit: int = Query(5, description="Number of recent uploads to consider")
):
    """
    Generate improvement suggestions based on recent perception data and history trends.
    Skips areas the user has already improved upon.
    """
    agent = FixitAgent()
    res = agent.run(AgentInput(
        media_id=media_id or 0,
        url=None,
        data={
            "user_id": user_id,
            "media_id": media_id or 0,
            "recent_limit": recent_limit
        }
    ))

    if not res.success:
        raise HTTPException(status_code=400, detail=res.error)

    return res.data
