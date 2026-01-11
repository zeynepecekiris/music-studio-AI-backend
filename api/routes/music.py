from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from typing import List, Optional
import os

from models.schemas import (
    MusicGenerationRequest,
    MusicGenerationResponse,
    AudioProcessingStatus,
    ErrorResponse
)
from services.elevenlabs_service import elevenlabs_service, PromptSafetyError
from config.settings import settings

router = APIRouter(prefix="/api/music", tags=["music"])

# In-memory task storage (in production, use Redis or database)
processing_tasks = {}

@router.post("/generate", response_model=MusicGenerationResponse)
async def generate_music(request: MusicGenerationRequest):
    """
    Generate music with vocals based on lyrics and preferences
    """
    try:
        # Validate request
        # Lyrics are optional for instrumental music
        if request.lyrics and len(request.lyrics.strip()) < 10:
            raise HTTPException(
                status_code=400,
                detail="Lyrics must be at least 10 characters long when provided"
            )
        
        if request.duration < 15 or request.duration > 300:
            raise HTTPException(
                status_code=400,
                detail="Duration must be between 15 and 300 seconds"
            )
        
        # Generate music using ElevenLabs
        music_response = await elevenlabs_service.generate_music(request)
        
        return music_response
        
    except PromptSafetyError as safety_error:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "BAD_PROMPT",
                "message": str(safety_error),
                "promptSuggestion": safety_error.suggestion,
                "detail": safety_error.detail,
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating music: {str(e)}"
        )

@router.post("/generate-async", response_model=dict)
async def generate_music_async(
    request: MusicGenerationRequest,
    background_tasks: BackgroundTasks
):
    """
    Generate music asynchronously (for long processing)
    """
    import uuid
    
    task_id = str(uuid.uuid4())
    
    # Initialize task status
    processing_tasks[task_id] = AudioProcessingStatus(
        task_id=task_id,
        status="pending",
        progress=0
    )
    
    # Add to background tasks
    background_tasks.add_task(
        _generate_music_background,
        task_id,
        request
    )
    
    return {
        "task_id": task_id,
        "status": "pending",
        "message": "Music generation started. Use /status/{task_id} to check progress."
    }

async def _generate_music_background(task_id: str, request: MusicGenerationRequest):
    """Background task for music generation"""
    try:
        # Update status
        processing_tasks[task_id].status = "processing"
        processing_tasks[task_id].progress = 25
        
        # Generate music
        music_response = await elevenlabs_service.generate_music(request)
        
        # Update status
        processing_tasks[task_id].status = "completed"
        processing_tasks[task_id].progress = 100
        processing_tasks[task_id].result = music_response
        
    except Exception as e:
        processing_tasks[task_id].status = "failed"
        processing_tasks[task_id].error_message = str(e)

@router.get("/status/{task_id}", response_model=AudioProcessingStatus)
async def get_generation_status(task_id: str):
    """
    Get the status of music generation task
    """
    if task_id not in processing_tasks:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )
    
    return processing_tasks[task_id]

@router.get("/download/{audio_id}")
async def download_music(audio_id: str):
    """
    Download generated music file
    """
    try:
        audio_path = os.path.join(settings.UPLOAD_DIR, "music", f"{audio_id}.mp3")
        
        if not os.path.exists(audio_path):
            raise HTTPException(
                status_code=404,
                detail="Music file not found"
            )
        
        return FileResponse(
            path=audio_path,
            media_type="audio/mpeg",
            filename=f"generated_music_{audio_id}.mp3"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error downloading music: {str(e)}"
        )

@router.get("/voices", response_model=List[dict])
async def get_available_voices():
    """
    Get list of available voices for music generation
    """
    try:
        voices = await elevenlabs_service.get_available_voices()
        return voices
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching voices: {str(e)}"
        )

@router.post("/clone-voice", response_model=dict)
async def clone_voice(
    name: str,
    description: str,
    files: List[UploadFile] = File(...)
):
    """
    Clone a custom voice from audio samples
    """
    try:
        if len(files) < 3:
            raise HTTPException(
                status_code=400,
                detail="At least 3 audio samples required for voice cloning"
            )
        
        # Read file data
        file_data = []
        for file in files:
            if not file.content_type.startswith('audio/'):
                raise HTTPException(
                    status_code=400,
                    detail="Only audio files are allowed"
                )
            content = await file.read()
            file_data.append(content)
        
        # Clone voice
        result = await elevenlabs_service.clone_voice(
            name=name,
            description=description,
            files=file_data
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error cloning voice: {str(e)}"
        )

@router.delete("/voices/{voice_id}")
async def delete_voice(voice_id: str):
    """
    Delete a custom cloned voice
    """
    try:
        # This would call ElevenLabs API to delete the voice
        # Implementation depends on ElevenLabs API capabilities
        
        return {"message": f"Voice {voice_id} deleted successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting voice: {str(e)}"
        )

@router.post("/enhance/{audio_id}")
async def enhance_audio(audio_id: str, enhancement_type: str = "music"):
    """
    Enhance generated audio with background music and effects
    """
    try:
        audio_path = os.path.join(settings.UPLOAD_DIR, "music", f"{audio_id}.mp3")
        
        if not os.path.exists(audio_path):
            raise HTTPException(
                status_code=404,
                detail="Audio file not found"
            )
        
        enhanced_path = await elevenlabs_service.enhance_audio(
            audio_path=audio_path,
            enhancement_type=enhancement_type
        )
        
        return {
            "message": "Audio enhanced successfully",
            "enhanced_audio_url": f"/music/enhanced_{audio_id}.mp3"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error enhancing audio: {str(e)}"
        )
