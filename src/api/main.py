from fastapi import FastAPI
from src.api.routes import media, perception  # ⬅ added perception
from src.db.session import engine
from src.db.models import Base
from src.api.routes import media
from src.api.routes import vibe_compare
from src.api.routes import history
from src.api.routes import fixit
from src.api.routes import reverse_analysis
from src.api.routes import vibe_analysis
from src.api.routes import full_chain
from src.api.routes import social_graph
from src.api.routes import notifications
from src.api.routes import public
from src.api.routes import auth
from src.api.routes import storage

from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import os

# NEW
from src.core.rate_limit import init_rate_limiter


app = FastAPI(title="LifeMirror API")

# Automatically create missing tables from models on startup
@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=engine)
    await init_rate_limiter()


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

app.include_router(notifications.router, prefix="/notifications", tags=["notifications"])

app.include_router(public.router, prefix="/public", tags=["public"])

app.include_router(auth.router, prefix="/auth", tags=["auth"])

app.include_router(storage.router, prefix="/storage", tags=["storage"])


# --- Security & CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Basic security headers
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        resp: Response = await call_next(request)
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return resp

app.add_middleware(SecurityHeadersMiddleware)

# Routers
app.include_router(media.router, prefix="/media", tags=["media"])

@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}
