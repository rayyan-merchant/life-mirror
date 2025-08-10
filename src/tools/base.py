from pydantic import BaseModel
from typing import Any, Dict

class ToolInput(BaseModel):
    media_id: str
    url: str
    options: Dict[str, Any] = {}

class ToolResult(BaseModel):
    success: bool
    data: Dict[str, Any]
    error: str | None = None

class BaseTool:
    name = 'base'

    def run(self, input: ToolInput) -> ToolResult:
        raise NotImplementedError("Tool must implement run()")

