from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from src.agents.reverse_analysis_agent import ReverseAnalysisAgent, AgentInput

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

    return res.data
