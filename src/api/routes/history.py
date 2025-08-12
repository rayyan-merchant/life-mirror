from fastapi import APIRouter, HTTPException
from src.agents.perception_history_agent import PerceptionHistoryAgent, AgentInput

router = APIRouter()

@router.get("/perception-history")
def get_perception_history(user_id: int):
    agent = PerceptionHistoryAgent()
    res = agent.run(AgentInput(media_id=0, url=None, data={"user_id": user_id}))

    if not res.success:
        raise HTTPException(status_code=404, detail=res.error)

    return res.data
