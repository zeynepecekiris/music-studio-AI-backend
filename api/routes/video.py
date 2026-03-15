"""
Video API Routes (FastAPI)
music_video.mp4 loop + audio merge ile klip oluşturma
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import traceback
import os
import sys
import uuid
import re
import tempfile
import httpx

# Backend path'i ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from config.settings import settings

router = APIRouter(prefix="/api/video", tags=["video"])


class CreateClipRequest(BaseModel):
    audio_url: str
    song_title: str = "Music Clip"
    duration: int = 60  # şarkı süresi (saniye)


class CreateClipResponse(BaseModel):
    video_url: str
    clip_id: str
    status: str
    duration: int


def resolve_audio_to_local_path(audio_url: str) -> Optional[str]:
    """
    Audio URL'ini lokal dosya yoluna çevir.
    
    URL formatları:
    - http://192.168.x.x:8000/music/xxx.mp3  -> uploads/music/xxx.mp3
    - /music/xxx.mp3                           -> uploads/music/xxx.mp3
    - music/xxx.mp3                            -> uploads/music/xxx.mp3
    """
    # URL'den dosya adını çıkar
    filename = None
    
    # http://...../music/filename.mp3
    match = re.search(r'/music/([^/?#]+\.mp3)', audio_url)
    if match:
        filename = match.group(1)
    
    if not filename:
        # music/filename.mp3
        match = re.search(r'music/([^/?#]+\.mp3)', audio_url)
        if match:
            filename = match.group(1)
    
    if filename:
        local_path = os.path.join(settings.UPLOAD_DIR, "music", filename)
        if os.path.exists(local_path):
            return os.path.abspath(local_path)
    
    return None


@router.post("/create-clip", response_model=CreateClipResponse)
async def create_clip(request: CreateClipRequest):
    """
    POST /api/video/create-clip
    
    music_video.mp4'ü loop edip müzikle birleştirerek klip oluştur.
    5 saniyelik video, şarkı süresi boyunca döngüye alınır.
    """
    try:
        from services.video_service import VideoService
        
        print(f"🎬 Create clip request received:")
        print(f"  - Audio URL: {request.audio_url}")
        print(f"  - Song Title: {request.song_title}")
        print(f"  - Duration: {request.duration}s")
        
        clip_id = str(uuid.uuid4())[:8]

        # Videos output klasörünü oluştur
        videos_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "uploads", "videos"
        )
        os.makedirs(videos_dir, exist_ok=True)

        output_filename = f"clip_{clip_id}.mp4"
        output_path = os.path.join(videos_dir, output_filename)

        # Önce local path'te dene, yoksa uzaktan indir
        local_audio_path = resolve_audio_to_local_path(request.audio_url)
        tmp_audio_file = None

        if not local_audio_path:
            # Remote URL - geçici dosyaya indir
            if request.audio_url.startswith("http://") or request.audio_url.startswith("https://"):
                print(f"  - Downloading audio from remote URL: {request.audio_url}")
                try:
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        resp = await client.get(request.audio_url)
                        resp.raise_for_status()
                    tmp_audio_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
                    tmp_audio_file.write(resp.content)
                    tmp_audio_file.flush()
                    tmp_audio_file.close()
                    local_audio_path = tmp_audio_file.name
                    print(f"  - Audio downloaded to temp: {local_audio_path}")
                except Exception as dl_err:
                    raise FileNotFoundError(f"Could not download audio: {dl_err}")
            else:
                raise FileNotFoundError(
                    f"Audio file not found locally for URL: {request.audio_url}"
                )

        print(f"  - Local audio path: {local_audio_path}")

        try:
            # Video service ile klip oluştur
            video_service = VideoService()
            video_service.create_music_clip(
                audio_path=local_audio_path,
                song_title=request.song_title,
                duration=request.duration,
                output_path=output_path
            )
        finally:
            # Geçici dosyayı temizle
            if tmp_audio_file and os.path.exists(tmp_audio_file.name):
                os.unlink(tmp_audio_file.name)
        
        # Video URL'i oluştur
        video_url = f"/videos/{output_filename}"
        
        print(f"✅ Clip created: {video_url}")
        
        return CreateClipResponse(
            video_url=video_url,
            clip_id=clip_id,
            status="completed",
            duration=request.duration
        )
        
    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {str(e)}"
        )
    except Exception as e:
        print(f"❌ Clip creation error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Clip creation failed: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    GET /api/video/health
    Video servisi sağlık kontrolü
    """
    template_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        '..', 'assets', 'music_video.mp4'
    )
    template_exists = os.path.exists(template_path)
    
    return {
        'status': 'healthy',
        'service': 'video_clip_creation',
        'mode': 'local_asset_loop',
        'template_video_exists': template_exists,
    }
