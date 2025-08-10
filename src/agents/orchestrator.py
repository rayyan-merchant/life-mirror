from .face_agent import FaceAgent
from .fashion_agent import FashionAgent
from .posture_agent import PostureAgent
from .embedder_agent import EmbedderAgent
from .base_agent import AgentInput

class Orchestrator:
    def __init__(self):
        self.face_agent = FaceAgent()
        self.fashion_agent = FashionAgent()
        self.posture_agent = PostureAgent()
        self.embedder_agent = EmbedderAgent()

    def analyze_media(self, media_id, url, context=None):
        context = context or {}
        agent_input = AgentInput(media_id=media_id, url=url, context=context)

        embed_data = self.embedder_agent.run(agent_input)
        face_data = self.face_agent.run(agent_input)
        fashion_data = self.fashion_agent.run(agent_input)
        posture_data = self.posture_agent.run(agent_input)

        return {
            "embedding": embed_data.dict(),
            "faces": face_data.dict(),
            "fashion": fashion_data.dict(),
            "posture": posture_data.dict()
        }
