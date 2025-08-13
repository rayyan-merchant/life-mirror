from fastapi import FastAPI
from src.api.routes import media, perception  # ⬅ added perception
from src.db.session import engine
from src.db.models import Base
from src.api.routes import vibe_compare
from src.api.routes import history
from src.api.routes import fixit
from src.api.routes import reverse_analysis
from src.api.routes import vibe_analysis
from src.api.routes import full_chain
from src.api.routes import social_graph


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

app.include_router(fixit.router, prefix="/improvement", tags=["fixit"])

app.include_router(reverse_analysis.router, prefix="/analysis", tags=["reverse_analysis"])

app.include_router(vibe_analysis.router, prefix="/analysis", tags=["vibe_analysis"])

app.include_router(full_chain.router, prefix="/analysis", tags=["full_chain"])

app.include_router(social_graph.router, prefix="/graph", tags=["social_graph"])

@app.get("/health")
async def health_check():
    return {"status": "ok"}
