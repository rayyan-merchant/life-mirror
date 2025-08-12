from fastapi import FastAPI
from src.api.routes import media, perception  # ⬅ added perception
from src.db.session import engine
from src.db.models import Base

app = FastAPI(title="LifeMirror API")

# Automatically create missing tables from models on startup
@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=engine)

# Existing routes
app.include_router(media.router, prefix="/media", tags=["media"])

# New perception route
app.include_router(perception.router, prefix="/media", tags=["perception"])

@app.get("/health")
async def health_check():
    return {"status": "ok"}
