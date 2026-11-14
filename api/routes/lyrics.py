from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
import asyncio
from typing import Optional

from models.schemas import (
    LyricsGenerationRequest,
    LyricsResponse,
    ErrorResponse,
    RhymeRequest,
)
from services.openai_service import openai_service
from services.auth_service import get_current_user
from db.models import User

router = APIRouter(prefix="/api/lyrics", tags=["lyrics"])

@router.post("/generate", response_model=LyricsResponse)
async def generate_lyrics(request: LyricsGenerationRequest, current_user: User = Depends(get_current_user)):
    """
    Generate song lyrics based on user story and theme
    """
    try:
        # Validate request
        if not request.story or len(request.story.strip()) < 10:
            raise HTTPException(
                status_code=400, 
                detail="Story must be at least 10 characters long"
            )
        
        # Generate lyrics using OpenAI
        lyrics_response = await openai_service.generate_lyrics(
            story=request.story,
            theme=request.theme,
            language=request.language,
            title=request.title,
            style=request.style,
        )
        
        return lyrics_response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating lyrics: {str(e)}"
        )

@router.post("/rhyme", response_model=dict)
async def rhyme_lyrics(request: RhymeRequest, current_user: User = Depends(get_current_user)):
    """Kafiye Sihirbazı: stronger rhymes and flow, same song."""
    try:
        lyrics = await openai_service.rhyme_lyrics(
            lyrics=request.lyrics, story=request.story, style=request.style, language=request.language,
        )
        return {"lyrics": lyrics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error polishing lyrics: {str(e)}")


@router.post("/improve", response_model=dict)
async def improve_lyrics(
    original_lyrics: str,
    story: str,
    theme: str,
    current_user: User = Depends(get_current_user)
):
    """
    Improve existing lyrics based on feedback
    """
    try:
        from models.schemas import MusicTheme
        
        # Validate theme
        theme_enum = MusicTheme(theme)
        
        improved_lyrics = await openai_service.improve_lyrics(
            original_lyrics=original_lyrics,
            story=story,
            theme=theme_enum
        )
        
        return {
            "improved_lyrics": improved_lyrics,
            "original_lyrics": original_lyrics
        }
        
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid theme provided"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error improving lyrics: {str(e)}"
        )

@router.post("/title", response_model=dict)
async def generate_title(lyrics: str, theme: str, current_user: User = Depends(get_current_user)):
    """
    Generate a catchy title for the song
    """
    try:
        from models.schemas import MusicTheme
        
        theme_enum = MusicTheme(theme)
        
        title = await openai_service.generate_title(
            lyrics=lyrics,
            theme=theme_enum
        )
        
        return {
            "title": title,
            "theme": theme
        }
        
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid theme provided"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating title: {str(e)}"
        )
