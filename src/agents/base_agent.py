from pydantic import BaseModel
from typing import Any, Dict

class AgentInput(BaseModel):
    media_id: str
    url: str
    context: Dict[str, Any] = {}

class AgentOutput(BaseModel):
    success: bool
    data: Dict[str, Any]
    error: str | None = None

class BaseAgent:
    name = "base"

    def run(self, input: AgentInput) -> AgentOutput:
        raise NotImplementedError
