# This is a local orchestrator prototype (LangGraph will replace this with nodes/edges)
class Orchestrator:
    def __init__(self, tools):
        self.tools = tools

    def analyze_media(self, media_id, url, context):
        # 1) call Embedder (async)
        # 2) call FaceTool on portrait keyframe(s)
        # 3) call DetectTool (fashion)
        # 4) call PostureTool
        # 5) aggregate
        pass
