#!/usr/bin/env python3
"""
Musician API Server Startup Script
"""

import os
import sys
import uvicorn
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Import app
from app.main import app
from config.settings import settings

def main():
    """Run the FastAPI server"""
    print("🎵 Starting Musician API Server...")
    print(f"🌐 Host: {settings.HOST}")
    print(f"🔌 Port: {settings.PORT}")
    print(f"🔧 Debug: {settings.DEBUG}")
    print(f"📁 Upload Dir: {settings.UPLOAD_DIR}")
    
    # Check API keys
    if not settings.OPENAI_API_KEY:
        print("⚠️  WARNING: OpenAI API key not configured")
    else:
        print("✅ OpenAI API key configured")
        
    if not settings.ELEVENLABS_API_KEY:
        print("⚠️  WARNING: ElevenLabs API key not configured")
    else:
        print("✅ ElevenLabs API key configured")
    
    print("\n🚀 Server starting...")
    print(f"📖 API Documentation: http://{settings.HOST}:{settings.PORT}/docs")
    print(f"🔍 ReDoc: http://{settings.HOST}:{settings.PORT}/redoc")
    
    # Run server
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning",
        access_log=settings.DEBUG
    )

if __name__ == "__main__":
    main()
