from fastapi import FastAPI
from src.api.routes import media, perception  # ⬅ added perception
from src.db.session import engine
from src.db.models import Base
from src.api.routes import vibe_compare
from src.api.routes import history


app = FastAPI(title="LifeMirror API")

# Automatically create missing tables from models on startup
@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=engine)

# Existing routes
app.include_router(media.router, prefix="/media", tags=["media"])

# New perception route
app.include_router(perception.router, prefix="/media", tags=["perception"])

app.include_router(vibe_compare.router, prefix="/compare", tags=["compare"])

app.include_router(history.router, prefix="/history", tags=["history"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}
