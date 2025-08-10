import os
from langgraph.graph import StateGraph
from langgraph.types import Node
from .base_agent import AgentInput
from .embedder_agent import EmbedderAgent
from .face_agent import FaceAgent
from .fashion_agent import FashionAgent
from .posture_agent import PostureAgent

class GraphExecutor:
    def __init__(self):
        self.graph = StateGraph()

        # Create agents
        self.embedder_agent = EmbedderAgent()
        self.face_agent = FaceAgent()
        self.fashion_agent = FashionAgent()
        self.posture_agent = PostureAgent()

        # Add nodes
        self.graph.add_node("embedding", self.run_embedder)
        self.graph.add_node("face", self.run_face)
        self.graph.add_node("fashion", self.run_fashion)
        self.graph.add_node("posture", self.run_posture)

        # Connect edges
        self.graph.add_edge("embedding", "face")
        self.graph.add_edge("face", "fashion")
        self.graph.add_edge("fashion", "posture")

        # Mark entry point
        self.graph.set_entry_point("embedding")

    def run_embedder(self, state):
        input_data = AgentInput(**state)
        res = self.embedder_agent.run(input_data)
        return {"embedding": res.dict(), **state}

    def run_face(self, state):
        input_data = AgentInput(**state)
        res = self.face_agent.run(input_data)
        return {"faces": res.dict(), **state}

    def run_fashion(self, state):
        input_data = AgentInput(**state)
        res = self.fashion_agent.run(input_data)
        return {"fashion": res.dict(), **state}

    def run_posture(self, state):
        input_data = AgentInput(**state)
        res = self.posture_agent.run(input_data)
        return {"posture": res.dict(), **state}

    def execute(self, media_id: str, url: str, context: dict = None):
        context = context or {}
        initial_state = {"media_id": media_id, "url": url, "context": context}
        return self.graph.run(initial_state)
