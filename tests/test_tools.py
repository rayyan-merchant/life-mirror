from uuid import uuid4
from src.tools.face_tool import FaceTool
from src.tools.detect_tool import DetectTool
from src.tools.embed_tool import EmbedTool
from src.tools.base import ToolInput

def test_embed_tool_deterministic():
    mid = str(uuid4())
    inp = ToolInput(media_id=mid, url="http://mock", options={"dims": 5})
    res1 = EmbedTool().run(inp)
    res2 = EmbedTool().run(inp)
    assert res1.success
    assert res1.data["vector"] == res2.data["vector"]

def test_face_tool_mock():
    inp = ToolInput(media_id=str(uuid4()), url="http://mock")
    res = FaceTool().run(inp)
    assert res.success
    assert "faces" in res.data
    assert len(res.data["faces"]) > 0

def test_detect_tool_mock():
    inp = ToolInput(media_id=str(uuid4()), url="http://mock")
    res = DetectTool().run(inp)
    assert res.success
    labels = [d["label"] for d in res.data["detections"]]
    assert "person" in labels

