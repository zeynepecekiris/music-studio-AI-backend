from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import os
import sys
import uvicorn

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from config.settings import settings
from api.routes import lyrics, music
from api.routes import download_routes  # NEW: Download routes for MP3 files
from models.schemas import HealthCheck

# Create FastAPI app
app = FastAPI(
    title="Music Studio AI API",
    description="AI-powered music and lyrics generation service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create upload directories
os.makedirs(os.path.join(settings.UPLOAD_DIR, "music"), exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_DIR, "voices"), exist_ok=True)

# Mount static files
app.mount("/music", StaticFiles(directory=os.path.join(settings.UPLOAD_DIR, "music")), name="music")
app.mount("/voices", StaticFiles(directory=os.path.join(settings.UPLOAD_DIR, "voices")), name="voices")

# Include routers
app.include_router(lyrics.router)
app.include_router(music.router)
app.include_router(download_routes.router)  # NEW: Download routes

@app.get("/", response_model=HealthCheck)
async def health_check():
    """Health check endpoint"""
    return HealthCheck(
        status="healthy",
        services={
            "openai": "connected" if settings.OPENAI_API_KEY else "not_configured",
            "elevenlabs": "connected" if settings.ELEVENLABS_API_KEY else "not_configured",
        }
    )

@app.get("/api/health", response_model=HealthCheck)
async def api_health_check():
    """API Health check endpoint"""
    return HealthCheck(
        status="healthy",
        services={
            "openai": "connected" if settings.OPENAI_API_KEY else "not_configured",
            "elevenlabs": "connected" if settings.ELEVENLABS_API_KEY else "not_configured",
        }
    )

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Not Found", "message": "The requested resource was not found"}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "message": "An unexpected error occurred"}
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
