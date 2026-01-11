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
        
        # Language-specific system prompts and instructions
        language_config = {
            "tr": {
                "system": "Sen profesyonel bir şarkı sözü yazarısın. Kullanıcıların hikayelerini duygusal ve kaliteli şarkı sözlerine dönüştürüyorsun.",
                "user_prefix": "Kullanıcının Hikayesi:",
                "instructions": "Lütfen bu hikayeye uygun, {theme} temalı bir şarkı sözü yazın. Şarkı sözü:\n- 4 kıta (verse) olsun\n- Her kıta 4 satır olsun\n- Nakarat (chorus) ekleyin\n- Duygusal ve akılda kalıcı olsun\n- Hikayedeki detayları kullanın\n- Türkçe olarak yazın\n- Şarkı formatında olsun (Verse 1, Chorus, Verse 2, vs.)"
            },
            "en": {
                "system": "You are a professional songwriter. You transform users' stories into emotional and high-quality song lyrics.",
                "user_prefix": "User's Story:",
                "instructions": "Please write song lyrics based on this story with the theme of {theme}. The lyrics should:\n- Have 4 verses\n- Each verse has 4 lines\n- Include a chorus\n- Be emotional and memorable\n- Use details from the story\n- Be written in English\n- Follow song format (Verse 1, Chorus, Verse 2, etc.)"
            },
            "es": {
                "system": "Eres un compositor profesional. Transformas las historias de los usuarios en letras de canciones emotivas y de alta calidad.",
                "user_prefix": "Historia del Usuario:",
                "instructions": "Por favor escribe una letra de canción basada en esta historia con el tema de {theme}. La letra debe:\n- Tener 4 estrofas\n- Cada estrofa tiene 4 líneas\n- Incluir un coro\n- Ser emotiva y memorable\n- Usar detalles de la historia\n- Estar escrita en español\n- Seguir el formato de canción (Estrofa 1, Coro, Estrofa 2, etc.)"
            },
            "ar": {
                "system": "أنت كاتب أغاني محترف. تحول قصص المستخدمين إلى كلمات أغاني عاطفية وعالية الجودة.",
                "user_prefix": "قصة المستخدم:",
                "instructions": "يرجى كتابة كلمات أغنية بناءً على هذه القصة بموضوع {theme}. يجب أن تكون الكلمات:\n- تحتوي على 4 مقاطع\n- كل مقطع يحتوي على 4 أسطر\n- تتضمن جوقة\n- عاطفية ولا تُنسى\n- تستخدم تفاصيل من القصة\n- مكتوبة بالعربية\n- تتبع شكل الأغنية"
            },
            "de": {
                "system": "Du bist ein professioneller Songwriter. Du verwandelst die Geschichten der Benutzer in emotionale und hochwertige Songtexte.",
                "user_prefix": "Geschichte des Benutzers:",
                "instructions": "Bitte schreibe einen Songtext basierend auf dieser Geschichte mit dem Thema {theme}. Der Text sollte:\n- 4 Strophen haben\n- Jede Strophe hat 4 Zeilen\n- Einen Refrain enthalten\n- Emotional und einprägsam sein\n- Details aus der Geschichte verwenden\n- Auf Deutsch geschrieben sein\n- Dem Songformat folgen"
            },
            "fr": {
                "system": "Tu es un parolier professionnel. Tu transformes les histoires des utilisateurs en paroles de chansons émotionnelles et de haute qualité.",
                "user_prefix": "Histoire de l'utilisateur:",
                "instructions": "Veuillez écrire des paroles de chanson basées sur cette histoire avec le thème de {theme}. Les paroles doivent:\n- Avoir 4 couplets\n- Chaque couplet a 4 lignes\n- Inclure un refrain\n- Être émotionnelles et mémorables\n- Utiliser des détails de l'histoire\n- Être écrites en français\n- Suivre le format de chanson"
            },
            "ko": {
                "system": "당신은 전문 작사가입니다. 사용자의 이야기를 감성적이고 고품질의 가사로 변환합니다.",
                "user_prefix": "사용자 이야기:",
                "instructions": "{theme} 테마로 이 이야기를 바탕으로 가사를 작성해주세요. 가사는:\n- 4개의 절을 가져야 합니다\n- 각 절은 4줄입니다\n- 후렴구를 포함합니다\n- 감성적이고 기억에 남아야 합니다\n- 이야기의 세부 사항을 사용합니다\n- 한국어로 작성되어야 합니다"
            },
            "zh": {
                "system": "你是一位专业的作词人。你将用户的故事转化为情感丰富、高质量的歌词。",
                "user_prefix": "用户故事:",
                "instructions": "请根据这个故事写一首以{theme}为主题的歌词。歌词应该:\n- 有4段\n- 每段4行\n- 包含副歌\n- 富有情感且令人难忘\n- 使用故事中的细节\n- 用中文写作"
            },
            "it": {
                "system": "Sei un paroliere professionista. Trasformi le storie degli utenti in testi di canzoni emotivi e di alta qualità.",
                "user_prefix": "Storia dell'utente:",
                "instructions": "Per favore scrivi un testo di canzone basato su questa storia con il tema di {theme}. Il testo dovrebbe:\n- Avere 4 strofe\n- Ogni strofa ha 4 righe\n- Includere un ritornello\n- Essere emotivo e memorabile\n- Usare dettagli dalla storia\n- Essere scritto in italiano"
            }
        }
        
        # Get language-specific configuration (default to English if not found)
        lang = language_config.get(request.language, language_config["en"])
        
        full_prompt = f"""
{lang['user_prefix']} "{request.story}"

{lang['instructions'].format(theme=request.theme)}

Format:
[Verse 1]
...

[Chorus] 
...

[Verse 2]
...

[Chorus]
...
"""

        print(f"🎵 Generating lyrics in {request.language} for theme: {request.theme}")

        # Call OpenAI API
        response = await openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system", 
                    "content": lang['system']
                },
                {
                    "role": "user", 
                    "content": full_prompt
                }
            ],
            max_tokens=1500,
            temperature=0.8
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

if __name__ == "__main__":
    print("🎵 Starting Musician Test Server...")
    print("📖 Visit http://localhost:8000/docs for API documentation")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
