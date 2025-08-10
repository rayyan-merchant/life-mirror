from .celery_app import celery
from src.tools.face_tool import FaceTool
from src.tools.detect_tool import DetectTool
from src.tools.embed_tool import EmbedTool
from src.tools.base import ToolInput
from src.utils.mock import load_mock_image

@celery.task(name='src.workers.tasks.process_media')
def process_media_async(media_id: str, storage_url: str):
    # Mock download
    img_bytes = load_mock_image()

    # Prepare tool input
    tool_input = ToolInput(media_id=media_id, url=storage_url)

    # Embed
    embed_res = EmbedTool().run(tool_input)
    print(f"[EmbedTool] {embed_res}")

    # Face detection
    face_res = FaceTool().run(tool_input)
    print(f"[FaceTool] {face_res}")

    # Object detection
    detect_res = DetectTool().run(tool_input)
    print(f"[DetectTool] {detect_res}")

    # TODO: Save results to DB (faces, detections, embeddings)
