import os
import sys
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from config.settings import settings
from api.routes import lyrics, music, video, download_routes
from api.routes import auth, songs, friends, messages, ws, wall, ads, lyrics_drafts
from models.schemas import HealthCheck

# Create all tables on startup (Alembic handles migrations in production)
from db.base import engine, Base
import db.models  # noqa: ensure models are registered
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Music Studio AI API",
    description="AI-powered music generation + social platform",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Upload directories
for sub in ("music", "voices", "videos"):
    os.makedirs(os.path.join(settings.UPLOAD_DIR, sub), exist_ok=True)

# --- Routers ---
# Existing
app.include_router(lyrics.router)
app.include_router(music.router)
app.include_router(download_routes.router)
app.include_router(video.router)

# New social platform routes
app.include_router(auth.router)
app.include_router(songs.router)
app.include_router(friends.router)
app.include_router(messages.router)
app.include_router(ws.router)
app.include_router(wall.router)
app.include_router(ads.router)
app.include_router(lyrics_drafts.router)

# Static files
app.mount("/music", StaticFiles(directory=os.path.join(settings.UPLOAD_DIR, "music"), check_dir=False), name="music")
app.mount("/voices", StaticFiles(directory=os.path.join(settings.UPLOAD_DIR, "voices"), check_dir=False), name="voices")
app.mount("/videos", StaticFiles(directory=os.path.join(settings.UPLOAD_DIR, "videos"), check_dir=False), name="videos")
app.mount("/avatars", StaticFiles(directory=os.path.join(settings.UPLOAD_DIR, "avatars"), check_dir=False), name="avatars")


@app.get("/", response_model=HealthCheck)
async def health_check():
    return HealthCheck(
        status="healthy",
        services={
            "openai": "connected" if settings.OPENAI_API_KEY else "not_configured",
            "elevenlabs": "connected" if settings.ELEVENLABS_API_KEY else "not_configured",
            "storage": "s3" if settings.S3_BUCKET_NAME else "local",
        },
    )


@app.get("/api/health", response_model=HealthCheck)
async def api_health_check():
    return HealthCheck(
        status="healthy",
        services={
            "openai": "connected" if settings.OPENAI_API_KEY else "not_configured",
            "elevenlabs": "connected" if settings.ELEVENLABS_API_KEY else "not_configured",
            "storage": "s3" if settings.S3_BUCKET_NAME else "local",
        },
    )


@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(status_code=404, content={"error": "Not Found"})


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(status_code=500, content={"error": "Internal Server Error"})


if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG, log_level="info")
