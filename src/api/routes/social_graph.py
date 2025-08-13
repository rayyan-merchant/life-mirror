from fastapi import APIRouter, HTTPException, Query
from src.agents.social_graph_agent import SocialGraphAgent, AgentInput

router = APIRouter()

@router.get("/social-graph")
def social_graph(user_id: int = Query(..., description="User ID to analyze")):
    agent = SocialGraphAgent()
    res = agent.run(AgentInput(media_id=0, url=None, data={"user_id": user_id}))
    if not res.success:
        raise HTTPException(status_code=400, detail=res.error)
    return res.data
