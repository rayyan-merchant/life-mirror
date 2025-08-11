import os
from .base_agent import BaseAgent, AgentInput, AgentOutput
from src.tools.embed_tool import EmbedTool
from src.tools.base import ToolInput

class EmbedderAgent(BaseAgent):
    name = "embedder_agent"
    output_schema = AgentOutput

    def run(self, input: AgentInput) -> AgentOutput:
        tool_input = ToolInput(media_id=input.media_id, url=input.url)
        res = EmbedTool().run(tool_input)

        if res.success:
            result = AgentOutput(success=True, data=res.data)
        else:
            result = AgentOutput(success=False, data={}, error=res.error)

        self._trace(input.dict(), result.dict())
        return result
