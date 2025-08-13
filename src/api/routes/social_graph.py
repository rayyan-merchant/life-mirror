from fastapi import APIRouter, HTTPException, Query
from src.agents.social_graph_agent import SocialGraphAgent, AgentInput
from src.db.session import get_db
from src.db.models import Media
from src.workers.tasks import _update_media_metadata

router = APIRouter()

@router.get("/social-graph")
def social_graph(user_id: int = Query(..., description="User ID to analyze")):
    agent = SocialGraphAgent()
    res = agent.run(AgentInput(media_id=0, url=None, data={"user_id": user_id}))
    db = next(get_db())
    latest_media = (
        db.query(Media)
        .filter(Media.user_id == user_id)
        .order_by(Media.created_at.desc())
        .first()
    )
    if latest_media:
        _update_media_metadata(db, latest_media.id, {"social_graph": res.data})
        
    if not res.success:
        raise HTTPException(status_code=400, detail=res.error)
    return res.data

# in social_graph.py after success




