import os
from .base_agent import BaseAgent, AgentInput, AgentOutput
from src.tools.embed_tool import EmbedTool
from src.tools.base import ToolInput

class EmbedderAgent(BaseAgent):
    name = "embedder_agent"

    def run(self, input: AgentInput) -> AgentOutput:
        mode = os.getenv("LIFEMIRROR_MODE", "mock")
        tool_input = ToolInput(media_id=input.media_id, url=input.url)
        res = EmbedTool().run(tool_input)
        if res.success:
            return AgentOutput(success=True, data=res.data)
        return AgentOutput(success=False, data={}, error=res.error)
