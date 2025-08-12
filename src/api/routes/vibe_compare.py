from fastapi import APIRouter, HTTPException
from src.agents.vibe_compare_agent import VibeComparisonAgent, AgentInput

router = APIRouter()

@router.get("/vibe-comparison")
def compare_vibes(media_id_1: int, media_id_2: int):
    agent = VibeComparisonAgent()
    res = agent.run(AgentInput(media_id=0, url=None, data={
        "media_id_1": media_id_1,
        "media_id_2": media_id_2
    }))

    if not res.success:
        raise HTTPException(status_code=500, detail=res.error)

    return res.data
