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

        # --- PROD MODE ---
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            # Step 1: Download the image (OpenAI embeddings API currently works on text, so we convert)
            # Option 1: For now, let's embed the URL string itself for quick retrieval use cases.
            # Option 2: If we want image embeddings, use CLIP or another vision model later.
            response = client.embeddings.create(
                model="text-embedding-3-large",
                input=input.url
            )
            vector = response.data[0].embedding
            return ToolResult(success=True, data={"vector": vector, "model": "text-embedding-3-large"})

        except Exception as e:
            return ToolResult(success=False, data={}, error=str(e))
