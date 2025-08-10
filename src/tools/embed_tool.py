import os
import random
from .base import BaseTool, ToolInput, ToolResult

class EmbedTool(BaseTool):
    name = 'embed'

    def run(self, input: ToolInput) -> ToolResult:
        mode = os.getenv("LIFEMIRROR_MODE", "mock")
        dims = input.options.get("dims", 8)
        if mode == "mock":
            seed = hash(input.media_id) % (2**32)
            rng = random.Random(seed)
            vector = [rng.uniform(-1, 1) for _ in range(dims)]
            return ToolResult(
                success=True,
                data={"vector": vector, "model": "mock-embed-v1"}
            )
        # TODO: implement real embedding model
        return ToolResult(success=False, data={}, error="Prod mode not implemented yet")

