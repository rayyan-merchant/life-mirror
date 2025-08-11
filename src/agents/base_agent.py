from pydantic import BaseModel
from typing import Any, Dict
from src.utils.tracing import log_trace
from src.utils.validation import guardrails_validate

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
    output_schema = AgentOutput  # Default schema, override in subclasses

    @guardrails_validate(AgentInput, AgentOutput)
    def run(self, input: AgentInput) -> AgentOutput:
        raise NotImplementedError

    def _trace(self, inputs: dict, outputs: dict):
        log_trace(self.name, inputs, outputs)
