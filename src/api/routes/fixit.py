from fastapi import APIRouter, HTTPException
from src.agents.fixit_agent import FixitAgent, AgentInput

router = APIRouter()

@router.get("/fixit-suggestions")
def get_fixit_suggestions(media_id: int, user_id: int):
    agent = FixitAgent()
    res = agent.run(AgentInput(media_id=media_id, url=None, data={"user_id": user_id, "media_id": media_id}))

    if not res.success:
        raise HTTPException(status_code=500, detail=res.error)

    return res.data
