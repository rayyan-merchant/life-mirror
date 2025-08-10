from fastapi import FastAPI
from src.api.routes import media
from src.db.session import engine
from src.db.models import Base

app = FastAPI(title="LifeMirror API")

# Automatically create missing tables from models on startup
@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=engine)

app.include_router(media.router, prefix="/media", tags=["media"])

@app.get("/health")
async def health_check():
    return {"status": "ok"}
