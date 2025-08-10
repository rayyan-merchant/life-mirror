from fastapi import FastAPI
from src.api.routes import media

app = FastAPI(title="LifeMirror API")

app.include_router(media.router, prefix="/media", tags=["media"])

@app.get("/health")
async def health_check():
    return {"status": "ok"}
