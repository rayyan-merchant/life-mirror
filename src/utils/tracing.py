import os
from langsmith import Client

_langsmith_enabled = bool(os.getenv("LANGSMITH_API_KEY"))
_client = Client(api_key=os.getenv("LANGSMITH_API_KEY")) if _langsmith_enabled else None

def log_trace(name: str, inputs: dict, outputs: dict):
    if not _langsmith_enabled or not _client:
        return
    _client.create_run(
        name=name,
        inputs=inputs,
        outputs=outputs,
        tags=["lifemirror", "agent"]
    )
