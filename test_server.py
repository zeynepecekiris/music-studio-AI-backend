#!/usr/bin/env python3
"""
Simple test server for Musician API with OpenAI integration
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
import os
import asyncio
import openai
from dotenv import load_dotenv
from typing import Dict, Optional
import uuid
import time
# from pydub import AudioSegment  # Temporarily disabled due to Python 3.13 compatibility
# from background_music_generator import BackgroundMusicGenerator

# Load environment variables
load_dotenv()

# Initialize OpenAI
openai_client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

# ElevenLabs client (optional)
try:
    from elevenlabs import ElevenLabs
    eleven_client: Optional[ElevenLabs] = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY", "")) if os.getenv("ELEVENLABS_API_KEY") else None
except Exception:
    eleven_client = None

# Background music generator (temporarily disabled)
# bg_music_generator = BackgroundMusicGenerator()

# Ensure static directories exist
os.makedirs("static/music", exist_ok=True)

# Create FastAPI app (must be defined before using app.mount)
app = FastAPI(
    title="Musician API - Test Server",
    description="AI-powered music and lyrics generation service",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In development, allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static for serving generated audio
app.mount("/music", StaticFiles(directory="static/music"), name="music")

# In-memory task storage
TASKS: Dict[str, Dict] = {}

# Theme-specific prompts
THEME_PROMPTS = {
    "love": {
        "tr": "Aşk temalı, romantik ve duygusal bir şarkı sözü yazın.",
        "en": "Write romantic and emotional song lyrics about love.",
        "es": "Escribe letras románticas y emocionales sobre el amor."
    },
    "friendship": {
        "tr": "Dostluk temalı, arkadaşlık bağının gücünü anlatan şarkı sözü yazın.",
        "en": "Write song lyrics about friendship and its power.",
        "es": "Escribe letras sobre la amistad y su poder."
    },
    "country": {
        "tr": "Memleket sevgisi temalı şarkı sözü yazın.",
        "en": "Write song lyrics about homeland love.",
        "es": "Escribe letras sobre el amor a la patria."
    },
    "nostalgia": {
        "tr": "Nostalji temalı, geçmişin güzel anılarını anlatan şarkı sözü yazın.",
        "en": "Write nostalgic song lyrics about beautiful memories from the past.",
        "es": "Escribe letras nostálgicas sobre hermosos recuerdos del pasado."
    },
    "hope": {
        "tr": "Umut temalı, gelecekteki güzel günlere olan inancı anlatan şarkı sözü yazın.",
        "en": "Write hopeful song lyrics about faith in beautiful future days.",
        "es": "Escribe letras esperanzadoras sobre la fe en días futuros hermosos."
    },
    "family": {
        "tr": "Aile temalı, ailenin sıcaklığını anlatan şarkı sözü yazın.",
        "en": "Write family-themed song lyrics about family warmth.",
        "es": "Escribe letras familiares sobre la calidez familiar."
    },
    "adventure": {
        "tr": "Macera temalı, yeni yerler keşfetmeyi anlatan şarkı sözü yazın.",
        "en": "Write adventure-themed song lyrics about discovering new places.",
        "es": "Escribe letras de aventura sobre descubrir nuevos lugares."
    },
    "peace": {
        "tr": "Barış temalı, iç huzuru ve sakinliği anlatan şarkı sözü yazın.",
        "en": "Write peace-themed song lyrics about inner peace and tranquility.",
        "es": "Escribe letras de paz sobre la paz interior y la tranquilidad."
    },
    "heartbreak": {
        "tr": "Kırık kalp temalı, ayrılık acısını anlatan şarkı sözü yazın.",
        "en": "Write heartbreak-themed song lyrics about the pain of separation.",
        "es": "Escribe letras de desamor sobre el dolor de la separación."
    },
    "happiness": {
        "tr": "Mutluluk temalı, yaşamın güzel anlarını anlatan şarkı sözü yazın.",
        "en": "Write happiness-themed song lyrics about life's beautiful moments.",
        "es": "Escribe letras de felicidad sobre los hermosos momentos de la vida."
    },
    "sadness": {
        "tr": "Hüzün temalı, üzüntü ve duygusal derinliği anlatan şarkı sözü yazın.",
        "en": "Write sadness-themed song lyrics about sorrow and emotional depth.",
        "es": "Escribe letras de tristeza sobre la pena y la profundidad emocional."
    },
    "celebration": {
        "tr": "Kutlama temalı, başarıları ve mutlu anları kutlayan şarkı sözü yazın.",
        "en": "Write celebration-themed song lyrics celebrating achievements and happy moments.",
        "es": "Escribe letras de celebración celebrando logros y momentos felices."
    },
    "motivation": {
        "tr": "Motivasyon temalı, ilham verici ve güçlendirici şarkı sözü yazın.",
        "en": "Write motivation-themed song lyrics that are inspiring and empowering.",
        "es": "Escribe letras motivacionales que sean inspiradoras y empoderadoras."
    }
}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Musician API is running! 🎵",
        "status": "healthy",
        "version": "1.0.0"
    }

# Request/Response models
class LyricsRequest(BaseModel):
    story: str
    title: Optional[str] = None
    theme: str
    language: str = "tr"

class LyricsResponse(BaseModel):
    id: str
    lyrics: str
    theme: str
    language: str
    processing_time: float
    word_count: int

class MusicRequest(BaseModel):
    lyrics: str
    style: str
    instruments: list[str]
    duration: str
    mood: str
    language: str = "tr"

class MusicAsyncResponse(BaseModel):
    task_id: str
    status: str

class MusicStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[Dict] = None
    error_message: Optional[str] = None

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    openai_status = "connected" if os.getenv("OPENAI_API_KEY") else "not_configured"
    elevenlabs_status = "connected" if os.getenv("ELEVENLABS_API_KEY") else "not_configured"
    
    return {
        "status": "healthy",
        "services": {
            "openai": openai_status,
            "elevenlabs": elevenlabs_status
        }
    }

@app.post("/api/lyrics/generate", response_model=LyricsResponse)
async def generate_lyrics(request: LyricsRequest):
    """Generate song lyrics using OpenAI"""
    import time
    import uuid
    
    start_time = time.time()
    
    try:
        # Check if OpenAI API key is configured
        if not os.getenv("OPENAI_API_KEY"):
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")
        
        # Output language mapping
        output_lang_map = {
            "tr": "Türkçe", "en": "English", "es": "Spanish", "ar": "Arabic",
            "de": "German", "fr": "French", "ko": "Korean", "zh": "Chinese", "it": "Italian"
        }
        output_lang = output_lang_map.get(request.language, "English")

        # Language-specific system prompts
        system_prompts = {
            "tr": "Sen profesyonel bir şarkı sözü yazarısın. Verilen hikayeden ilham alarak özgün, duygusal ve şiirsel Türkçe şarkı sözleri yazarsın.",
            "en": "You are a professional songwriter who writes original, emotional, and poetic song lyrics in English based on the given story.",
            "es": "Eres un compositor profesional que escribe letras de canciones originales, emotivas y poéticas en español basadas en la historia dada.",
            "de": "Du bist ein professioneller Songwriter, der originelle, emotionale und poetische deutsche Songtexte basierend auf der gegebenen Geschichte schreibt.",
            "fr": "Tu es un parolier professionnel qui écrit des paroles de chansons originales, émotionnelles et poétiques en français basées sur l'histoire donnée.",
            "ko": "당신은 주어진 이야기를 바탕으로 독창적이고 감성적이며 시적인 한국어 노래 가사를 쓰는 전문 작사가입니다.",
            "zh": "你是一位专业的词曲作家，根据给定的故事创作原创、情感丰富且富有诗意的中文歌词。",
            "it": "Sei un paroliere professionista che scrive testi di canzoni originali, emotivi e poetici in italiano basati sulla storia data.",
            "ar": "أنت كاتب أغاني محترف يكتب كلمات أغاني أصلية وعاطفية وشعرية باللغة العربية بناءً على القصة المعطاة.",
        }

        system_msg = system_prompts.get(request.language, system_prompts["en"])

        # Build title line for prompt
        title_line = f'Title: "{request.title}"\n' if request.title else ""
        
        # Get theme-specific guidance
        theme_guidance = THEME_PROMPTS.get(request.theme, {}).get(request.language, "")
        
        # Create example to show the format
        example_format = """
Example format:
[Verse 1]
Golden beaches calling my name
Sunset colors paint the sky
Temple bells echo through the rain
Where the palm trees touch the sky

[Chorus]
Take me there, to that distant shore
Where my heart can finally soar
In the land of smiles and dreams
Nothing's ever as it seems

[Verse 2]
Street food vendors light the night
Tuk-tuks racing through the crowd
Ancient wisdom shining bright
In this place I'm finally found

[Bridge]
Every moment feels brand new
Every color, every view

[Final Chorus]
Take me there, to that distant shore
Where my heart can finally soar
In the land of smiles and dreams
Living out my wildest dreams
"""

        full_prompt = f"""You are a professional songwriter. Write original song lyrics in {output_lang}.

{title_line}Story/Inspiration: {request.story}
Theme: {request.theme}

{example_format}

Now write a COMPLETE ORIGINAL SONG in {output_lang} inspired by the story above. The song should:
- Be written ENTIRELY in {output_lang} (not English unless requested)
- Expand the story into vivid, emotional lyrics with imagery and metaphors
- Include these sections: [Verse 1], [Chorus], [Verse 2], [Bridge], [Final Chorus]
- Each verse should be 4-6 lines
- Chorus should be 3-4 catchy lines
- Bridge should be 2-4 lines
- Make every line unique and meaningful
- Use natural rhymes
- Tell a complete emotional story

IMPORTANT: Write ONLY the song lyrics with section headers. Do NOT copy or repeat the user's story text. Create NEW poetic lyrics inspired by the story's theme and emotion."""

        print(f"🎵 Generating lyrics in {request.language} for theme: {request.theme}, title: {request.title}")

        # Call OpenAI API
        response = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system", 
                    "content": system_msg
                },
                {
                    "role": "user", 
                    "content": full_prompt
                }
            ],
            max_tokens=2000,
            temperature=0.78,
            presence_penalty=0.7,
            frequency_penalty=0.8
        )
        
        lyrics = response.choices[0].message.content.strip()
        processing_time = time.time() - start_time
        word_count = len(lyrics.split())
        
        return LyricsResponse(
            id=str(uuid.uuid4()),
            lyrics=lyrics,
            theme=request.theme,
            language=request.language,
            processing_time=processing_time,
            word_count=word_count
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating lyrics: {str(e)}")

async def generate_music_job(task_id: str, req: MusicRequest):
    TASKS[task_id] = {"status": "processing"}
    audio_id = str(uuid.uuid4())
    final_path = f"static/music/{audio_id}.mp3"

    try:
        print(f"🎵 Generating REAL MUSIC for task {task_id}")
        print(f"🎵 Style: {req.style}, Instruments: {req.instruments}, Mood: {req.mood}")
        
        # Use ElevenLabs Music Generation API (Premium feature)
        if eleven_client:
            # Create detailed music prompt based on user selections
            instruments_text = ", ".join(req.instruments)
            
            music_prompt = f"""
            Create a {req.mood} {req.style} song with {instruments_text}. 
            The song should have a {req.mood} emotional tone.
            Musical style: {req.style}
            Instruments to feature: {instruments_text}
            Duration: {req.duration} seconds
            
            Incorporate these lyrical themes: {req.lyrics[:500] if req.lyrics else 'love and emotion'}
            
            Make it a complete musical composition with melody, harmony, and rhythm.
            """
            
            try:
                print(f"🎼 Generating REAL MUSIC with ElevenLabs Music Detailed API...")
                
                # Create proper music prompt for ElevenLabs Music API
                instruments_text = ", ".join(req.instruments)
                
                # Parse duration properly (handle "short", "medium", "long" or numeric values)
                duration_mapping = {
                    "short": 90,
                    "medium": 150, 
                    "long": 210
                }
                
                if req.duration in duration_mapping:
                    duration_seconds = duration_mapping[req.duration]
                else:
                    try:
                        duration_seconds = int(req.duration)
                    except:
                        duration_seconds = 150  # default
                
                duration_ms = duration_seconds * 1000
                
                # Map language codes to full language names for better prompt clarity
                language_names = {
                    "en": "English",
                    "tr": "Turkish",
                    "es": "Spanish",
                    "ar": "Arabic",
                    "de": "German",
                    "fr": "French",
                    "ko": "Korean",
                    "zh": "Chinese",
                    "it": "Italian"
                }
                
                language_name = language_names.get(req.language, "English")
                
                # Use lyrics in user's selected language
                if req.lyrics:
                    music_prompt = f"""
                    Create a {req.mood} {req.style} song with {instruments_text}.
                    {'Female' if req.mood in ['romantic', 'sad', 'melancholic'] else 'Male'} vocals singing in {language_name}.
                    Use these lyrics: {req.lyrics[:800]}
                    Make it emotional and catchy with verse-chorus structure.
                    Sing in {language_name} language.
                    """
                else:
                    music_prompt = f"""
                    Create a {req.mood} {req.style} song with {instruments_text}.
                    {'Female' if req.mood in ['romantic', 'sad', 'melancholic'] else 'Male'} vocals singing in {language_name}.
                    Theme: love and emotions. Create original {language_name} lyrics.
                    Make it emotional and catchy with verse-chorus-bridge structure.
                    Sing in {language_name} language.
                    """
                
                print(f"🎼 Music Prompt: {music_prompt[:150]}...")
                print(f"🎼 Duration: {duration_ms}ms ({duration_seconds}s)")
                
                # Use detailed endpoint to get composition plan + audio
                detailed_result = eleven_client.music.compose_detailed(
                    prompt=music_prompt,
                    music_length_ms=duration_ms,
                    model_id="music_v1"
                )
                
                print(f"🎵 Composition plan: {detailed_result.composition_plan}")
                print(f"🎵 Song metadata: {detailed_result.song_metadata}")
                
                # Save the generated music
                with open(final_path, "wb") as f:
                    f.write(detailed_result.audio)
                        
                print(f"✅ REAL MUSIC track created: {final_path}")
                print(f"🎵 File size: {os.path.getsize(final_path)} bytes")
                
                # Extract lyrics from composition plan if available
                generated_lyrics = ""
                if hasattr(detailed_result, 'composition_plan') and detailed_result.composition_plan:
                    sections = detailed_result.composition_plan.get('sections', [])
                    for section in sections:
                        if 'lines' in section:
                            generated_lyrics += f"[{section.get('section_name', 'Section')}]\n"
                            generated_lyrics += "\n".join(section['lines']) + "\n\n"
                
            except Exception as e:
                print(f"❌ Music API error: {e}")
                
                # Fallback to enhanced TTS if Music API fails
                print(f"🎤 Falling back to enhanced vocal generation...")
                musical_prompt = f"""
                *singing with {req.mood} emotion in {req.style} style*
                
                {req.lyrics[:1500] if req.lyrics else 'La la la, beautiful melody'}
                
                *humming melodically* 
                Hmm hmm hmm, la la la la...
                *musical outro*
                """
                
                voice_mapping = {
                    "romantic": "21m00Tcm4TlvDq8ikWAM",  # Rachel (female, warm)
                    "energetic": "AZnzlk1XvdvUeBnXmlld",  # Domi (male, energetic)  
                    "sad": "EXAVITQu4vr4xnSDxMaL",      # Bella (female, soft)
                    "happy": "TX3LPaxmHKxFdv7VOQHJ",     # Liam (male, cheerful)
                    "calm": "pNInz6obpgDQGcFmaJgB",      # Adam (male, calm)
                    "melancholic": "ThT5KcBeYPX3keUQqHPh"  # Dorothy (female, emotional)
                }
                
                voice_id = voice_mapping.get(req.mood, "21m00Tcm4TlvDq8ikWAM")
                
                audio = eleven_client.text_to_speech.convert(
                    voice_id=voice_id,
                    optimize_streaming_latency=0,
                    output_format="mp3_44100_128",
                    model_id="eleven_multilingual_v2",
                    text=musical_prompt
                )
                
                with open(final_path, "wb") as f:
                    for chunk in audio:
                        f.write(chunk)
                print(f"✅ Vocal track created as fallback: {final_path}")
        else:
            # No ElevenLabs, create placeholder
            with open(final_path, "wb") as f:
                f.write(b"\x00\x00")
        
        # Get song title from metadata or create default
        song_title = "AI Müzik"
        song_description = f"{req.mood} {req.style} with {', '.join(req.instruments)}"
        
        try:
            if 'detailed_result' in locals() and hasattr(detailed_result, 'song_metadata'):
                metadata = detailed_result.song_metadata
                if metadata and hasattr(metadata, 'title') and metadata.title:
                    song_title = metadata.title
                if metadata and hasattr(metadata, 'description') and metadata.description:
                    song_description = metadata.description
        except:
            pass

        TASKS[task_id] = {
            "status": "completed",
            "result": {
                "audio_id": audio_id,
                "audio_url": f"/music/{audio_id}.mp3",
                "title": song_title,
                "duration": req.duration,
                "style": req.style,
                "mood": req.mood,
                "instruments": req.instruments,
                "type": "ElevenLabs Music Generation",
                "description": song_description,
                "generated_lyrics": generated_lyrics if 'generated_lyrics' in locals() else None,
                "has_composition_plan": 'detailed_result' in locals() and hasattr(detailed_result, 'composition_plan')
            }
        }
        print(f"🎉 REAL MUSIC generation completed for task {task_id}")
        
    except Exception as e:
        print(f"❌ Music generation failed: {e}")
        TASKS[task_id] = {
            "status": "failed",
            "error_message": str(e)
        }

@app.post("/api/music/generate-async", response_model=MusicAsyncResponse)
async def music_generate_async(req: MusicRequest):
    task_id = str(uuid.uuid4())
    TASKS[task_id] = {"status": "queued"}
    asyncio.create_task(generate_music_job(task_id, req))
    return {"task_id": task_id, "status": "queued"}

@app.get("/api/music/status/{task_id}", response_model=MusicStatusResponse)
async def music_status(task_id: str):
    task = TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    resp: Dict = {"task_id": task_id, "status": task["status"]}
    if task["status"] == "completed":
        resp["result"] = task["result"]
    if task["status"] == "failed":
        resp["error_message"] = task.get("error_message")
    return resp

@app.get("/api/music/voices")
async def music_voices():
    if not eleven_client:
        return {"voices": []}
    try:
        voices = eleven_client.voices.get_all()
        return {"voices": [{"voice_id": v.voice_id, "name": v.name} for v in voices.voices]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/music/generate")
async def generate_music_direct(req: MusicRequest):
    """Direct music generation endpoint that streams MP3"""
    try:
        print(f"🎵 Direct music generation request: {req.style}, {req.mood}")
        
        if eleven_client:
            # Create proper music prompt for ElevenLabs Music API
            instruments_text = ", ".join(req.instruments)
            
            # Parse duration properly
            duration_mapping = {"short": 90, "medium": 150, "long": 210}
            if req.duration in duration_mapping:
                duration_seconds = duration_mapping[req.duration]
            else:
                try:
                    duration_seconds = int(req.duration)
                except:
                    duration_seconds = 150
            
            duration_ms = duration_seconds * 1000
            
            # Map language codes to full language names
            language_names = {
                "en": "English",
                "tr": "Turkish",
                "es": "Spanish",
                "ar": "Arabic",
                "de": "German",
                "fr": "French",
                "ko": "Korean",
                "zh": "Chinese",
                "it": "Italian"
            }
            
            language_name = language_names.get(req.language, "English")
            
            # Create music prompt with user's selected language
            if req.lyrics:
                music_prompt = f"""
                {language_name} lyrics, {req.style} style, {instruments_text} instrumentation, 
                {'female' if req.mood in ['romantic', 'sad', 'melancholic'] else 'male'} vocals.
                Theme: {req.mood}. Use these lyrics: {req.lyrics[:800]}
                Catchy chorus, verse-chorus structure. Sing in {language_name}.
                """
            else:
                music_prompt = f"""
                {language_name} lyrics, {req.style} style, {instruments_text} instrumentation,
                {'female' if req.mood in ['romantic', 'sad', 'melancholic'] else 'male'} vocals.
                Theme: {req.mood}. Create original {language_name} lyrics about love and emotions.
                Catchy chorus, verse-chorus-bridge structure. Sing in {language_name}.
                """
            
            try:
                print(f"🎼 Generating music with ElevenLabs Music Stream API...")
                print(f"🎵 Language: {language_name} ({req.language})")
                print(f"🎵 Prompt: {music_prompt[:200]}...")
                
                # Use stream endpoint for faster response
                audio_stream = eleven_client.music.stream(
                    prompt=music_prompt,
                    music_length_ms=duration_ms,
                    model_id="music_v1"
                )
                
                print(f"✅ Music stream started successfully")
                
                def generate_music_stream():
                    for chunk in audio_stream:
                        yield chunk
                
                return StreamingResponse(
                    generate_music_stream(),
                    media_type="audio/mpeg",
                    headers={"Content-Disposition": f'attachment; filename="song_{req.style}_{req.mood}.mp3"'}
                )
                
            except Exception as e:
                print(f"❌ Music API error: {e}")
                # Fallback to TTS
                return await generate_tts_fallback(req)
        else:
            return await generate_tts_fallback(req)
            
    except Exception as e:
        print(f"❌ Direct generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def generate_tts_fallback(req: MusicRequest):
    """Fallback TTS generation"""
    try:
        musical_prompt = f"""
        *singing with {req.mood} emotion in {req.style} style*
        
        {req.lyrics[:1500] if req.lyrics else 'La la la, beautiful melody'}
        
        *humming melodically* 
        Hmm hmm hmm, la la la la...
        *musical outro*
        """
        
        voice_mapping = {
            "romantic": "21m00Tcm4TlvDq8ikWAM",
            "energetic": "AZnzlk1XvdvUeBnXmlld",  
            "sad": "EXAVITQu4vr4xnSDxMaL",
            "happy": "TX3LPaxmHKxFdv7VOQHJ",
            "calm": "pNInz6obpgDQGcFmaJgB",
            "melancholic": "ThT5KcBeYPX3keUQqHPh"
        }
        
        voice_id = voice_mapping.get(req.mood, "21m00Tcm4TlvDq8ikWAM")
        
        audio = eleven_client.text_to_speech.convert(
            voice_id=voice_id,
            optimize_streaming_latency=0,
            output_format="mp3_44100_128",
            model_id="eleven_multilingual_v2",
            text=musical_prompt
        )
        
        def generate_audio():
            for chunk in audio:
                yield chunk
        
        return StreamingResponse(
            generate_audio(),
            media_type="audio/mpeg",
            headers={"Content-Disposition": f'attachment; filename="vocal_{req.style}_{req.mood}.mp3"'}
        )
        
    except Exception as e:
        print(f"❌ TTS fallback error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 🎬 INSTAGRAM STORY VIDEO ENDPOINTS
# ============================================================================

class VideoRequest(BaseModel):
    audio_url: str
    song_title: str
    artist_name: str
    duration: int
    genre: str = ""
    mood: str = ""

class VideoResponse(BaseModel):
    video_url: str
    task_id: str
    status: str

@app.post("/api/create-story-video", response_model=VideoResponse)
async def create_story_video(request: VideoRequest):
    """
    🎬 Instagram Story videosu oluştur
    
    Template video + Müzik = Instagram Story Video
    """
    try:
        from services.video_service import video_service
        
        print(f"🎬 Creating Instagram Story video for: {request.song_title}")
        
        # Task ID oluştur
        task_id = str(uuid.uuid4())
        
        # Video oluştur (async olarak)
        output_filename = f"story_{task_id}.mp4"
        output_path = os.path.join("static", "videos", output_filename)
        
        # Videos klasörü yoksa oluştur
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Video oluştur
        video_path = video_service.create_instagram_story_video(
            audio_url=request.audio_url,
            song_title=request.song_title,
            artist_name=request.artist_name,
            duration=request.duration,
            genre=request.genre,
            mood=request.mood,
            output_path=output_path
        )
        
        # Video URL'i oluştur
        video_url = f"/videos/{output_filename}"
        
        print(f"✅ Video created: {video_url}")
        
        return VideoResponse(
            video_url=video_url,
            task_id=task_id,
            status="completed"
        )
        
    except FileNotFoundError as e:
        print(f"❌ Template video not found: {e}")
        raise HTTPException(
            status_code=404,
            detail="Template video not found. Please add story-template.mp4 to backend/assets/"
        )
    except Exception as e:
        print(f"❌ Video creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/video-status/{task_id}")
async def get_video_status(task_id: str):
    """Video oluşturma durumunu kontrol et"""
    video_filename = f"story_{task_id}.mp4"
    video_path = os.path.join("static", "videos", video_filename)
    
    if os.path.exists(video_path):
        return {
            "task_id": task_id,
            "status": "completed",
            "video_url": f"/videos/{video_filename}"
        }
    else:
        return {
            "task_id": task_id,
            "status": "processing"
        }


# Mount videos directory
os.makedirs("static/videos", exist_ok=True)
app.mount("/videos", StaticFiles(directory="static/videos"), name="videos")


if __name__ == "__main__":
    print("🎵 Starting Musician Test Server...")
    print("📖 Visit http://localhost:8000/docs for API documentation")
    print("🎬 Instagram Story Video feature enabled!")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
