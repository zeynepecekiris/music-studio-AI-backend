import os
import uuid
import aiofiles
import json
import ast
from typing import Dict, Any, List, Optional
import asyncio
import time
from config.settings import settings
from models.schemas import (
    MusicGenerationRequest, 
    MusicGenerationResponse, 
    VoiceGender, 
    MusicGenre,
    MusicMood,
    Instrument
)
from elevenlabs.client import AsyncElevenLabs


class PromptSafetyError(Exception):
    """Raised when ElevenLabs rejects a prompt for policy/safety reasons."""

    def __init__(
        self,
        message: str,
        suggestion: Optional[str] = None,
        detail: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.suggestion = suggestion
        self.detail = detail or {}

class ElevenLabsService:
    def __init__(self):
        self.api_key = settings.ELEVENLABS_API_KEY
        self.base_url = "https://api.elevenlabs.io/v1"
        self.client = AsyncElevenLabs(api_key=self.api_key)
        
        # Voice IDs for singing (with text-to-speech)
        self.voice_ids = {
            VoiceGender.MALE: "pNInz6obpgDQGcFmaJgB",  # Adam - Deep, warm male voice
            VoiceGender.FEMALE: "EXAVITQu4vr4xnSDxMaL",  # Bella - Natural, friendly female
            VoiceGender.NEUTRAL: "21m00Tcm4TlvDq8ikWAM"  # Rachel - Clear, neutral voice
        }
        
        # Genre and mood descriptions for music generation
        self.genre_prompts = {
            MusicGenre.POP: "upbeat pop music with catchy melodies",
            MusicGenre.ROCK: "energetic rock music with electric guitars",
            MusicGenre.JAZZ: "smooth jazz with saxophone and piano",
            MusicGenre.BLUES: "soulful blues guitar",
            MusicGenre.CLASSICAL: "orchestral classical music",
            MusicGenre.ELECTRONIC: "electronic dance music",
            MusicGenre.ACOUSTIC: "acoustic guitar melody",
            MusicGenre.RAP: "hip hop beat",
            MusicGenre.FOLK: "folk music with acoustic instruments",
            MusicGenre.METAL: "heavy metal with distorted guitars",
            MusicGenre.COUNTRY: "country music with banjo",
            MusicGenre.RNB: "R&B with smooth vocals",
            MusicGenre.REGGAE: "reggae rhythm",
            # New genres
            MusicGenre.HOUSE: "deep house and progressive house electronic music",
            MusicGenre.TECHNO: "driving techno with industrial beats",
            MusicGenre.TRANCE: "uplifting trance with melodic leads",
            MusicGenre.DRUM_AND_BASS: "fast-paced drum and bass with heavy basslines",
            MusicGenre.DREAM_POP: "ethereal dream pop with reverb-drenched vocals",
            MusicGenre.TRIP_HOP: "atmospheric trip hop with downtempo beats",
            MusicGenre.CHILLWAVE: "nostalgic chillwave with synth textures",
            MusicGenre.OPERA: "classical opera with powerful vocals",
            MusicGenre.SYMPHONIC: "symphonic orchestral music",
            MusicGenre.K_POP: "Korean pop with modern production",
            MusicGenre.J_POP: "Japanese pop with anime-style melodies",
            MusicGenre.C_POP: "Chinese pop with contemporary arrangements",
            MusicGenre.BOLLYWOOD: "Bollywood film music with Indian instruments",
            MusicGenre.LATIN: "Latin music with salsa, bachata, and bossa nova",
            MusicGenre.FLAMENCO: "passionate flamenco with Spanish guitar",
            MusicGenre.DISCO: "funky disco with four-on-the-floor beats",
            MusicGenre.DANCEHALL: "Jamaican dancehall with reggae influences",
            MusicGenre.HIP_HOP: "urban hip hop with rap vocals",
            MusicGenre.TRAP: "modern trap with heavy 808s and hi-hats"
        }
        
        self.language_map = {
            "en": "English",
            "tr": "Turkish",
            "es": "Spanish",
            "de": "German",
            "fr": "French",
            "ko": "Korean",
            "zh": "Chinese",
            "it": "Italian",
            "ar": "Arabic"
        }
        
        self.instrument_prompts = {
            Instrument.GUITAR: "acoustic guitar strums",
            Instrument.ELECTRIC_GUITAR: "electric guitar riffs",
            Instrument.ACOUSTIC_GUITAR: "warm acoustic guitars",
            Instrument.BASS: "groovy bass guitar",
            Instrument.BASS_GUITAR: "deep bass guitar",
            Instrument.DRUMS: "punchy drum grooves",
            Instrument.PIANO: "emotional piano chords",
            Instrument.KEYBOARD: "modern keyboard layers",
            Instrument.SYNTHESIZER: "lush synthesizer pads",
            Instrument.VIOLIN: "expressive violin melodies",
            Instrument.CELLO: "rich cello strings",
            Instrument.FLUTE: "airy flute motifs",
            Instrument.SAXOPHONE: "soulful saxophone leads",
            Instrument.TRUMPET: "brass trumpet accents",
            Instrument.HARP: "gentle harp arpeggios",
        }

    async def generate_music(self, request: MusicGenerationRequest) -> MusicGenerationResponse:
        """Generate complete song using ElevenLabs Music API (vocals + instruments + lyrics)"""
        start_time = time.time()
        
        try:
            # Create unique filename
            audio_id = str(uuid.uuid4())
            audio_filename = f"{audio_id}.mp3"
            audio_path = os.path.join(settings.UPLOAD_DIR, "music", audio_filename)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(audio_path), exist_ok=True)
            
            # Build music prompt for ElevenLabs Music API
            prompt, language_name = self._build_complete_music_prompt(request)
            
            # Generate complete song using Music API
            audio_data = await self._generate_complete_song(
                prompt=prompt,
                lyrics=request.lyrics,
                duration_ms=request.duration * 1000,
                language_name=language_name
            )
            
            # Save audio file
            async with aiofiles.open(audio_path, 'wb') as f:
                await f.write(audio_data)
            
            # Get file size
            file_size = os.path.getsize(audio_path)
            
            # Create public URL
            audio_url = f"/music/{audio_filename}"
            
            processing_time = time.time() - start_time
            
            return MusicGenerationResponse(
                id=audio_id,
                audio_url=audio_url,
                lyrics=request.lyrics,
                story=request.story,
                theme=request.theme,
                genre=request.genre,
                voice_gender=request.voice_gender,
                mood=request.mood,
                instruments=request.instruments,
                tempo=request.tempo,
                duration=request.duration,
                processing_time=processing_time,
                file_size=file_size
            )
            
        except PromptSafetyError:
            # Propagate prompt safety issues so API layer can return better detail
            raise
        except Exception as e:
            raise Exception(f"Error generating music: {str(e)}")

    def _build_complete_music_prompt(self, request: MusicGenerationRequest) -> tuple[str, str]:
        """Build complete prompt for ElevenLabs Music API (vocals + instruments)"""
        
        genre_desc = self.genre_prompts.get(request.genre, "modern pop music")
        mood_desc = (request.mood.value.replace('_', ' ') if request.mood else "emotional").strip()
        
        instrument_descriptions = []
        if request.instruments:
            for inst in request.instruments:
                # Handle both Enum and string types
                if isinstance(inst, Instrument):
                    instrument_descriptions.append(
                        self.instrument_prompts.get(inst, inst.value.replace('_', ' '))
                    )
                else:
                    # If it's a string, try to find the matching Instrument enum
                    try:
                        inst_enum = Instrument(inst)
                        instrument_descriptions.append(
                            self.instrument_prompts.get(inst_enum, inst.replace('_', ' '))
                        )
                    except (ValueError, AttributeError):
                        # Fallback: just use the string value
                        instrument_descriptions.append(str(inst).replace('_', ' '))
        instruments_str = ", ".join(instrument_descriptions) if instrument_descriptions else "balanced drums, bass, guitars and synth layers"
        
        if request.voice_gender == VoiceGender.MALE:
            vocal_desc = "warm male vocals"
        elif request.voice_gender == VoiceGender.FEMALE:
            vocal_desc = "emotional female vocals"
        else:
            vocal_desc = "expressive vocals"
        
        language_code = (request.language or "en").lower()
        language = self.language_map.get(language_code, "English")
        
        story_excerpt = (request.story or "").strip().replace("\n", " ")
        if len(story_excerpt) > 400:
            story_excerpt = story_excerpt[:400].rstrip() + "..."
        
        theme_sentence = f"The lyrical theme is {request.theme.value}." if request.theme else ""
        
        prompt_parts = [
            f"Create a professional {genre_desc} song in {language} with a {mood_desc} mood.",
            f"CRITICAL: The song MUST start immediately with {instruments_str} playing from the very first second.",
            f"The instrumental arrangement with {instruments_str} must play throughout the ENTIRE song from start to finish.",
            f"DO NOT start with vocals only - instruments and vocals must play together from the beginning.",
            f"Feature {vocal_desc} singing in {language}.",
            f"Duration: {request.duration} seconds with verse-chorus structure.",
            theme_sentence,
        ]
        
        if story_excerpt:
            prompt_parts.append(f"Story inspiration: {story_excerpt}")
        
        prompt_parts.append(f"IMPORTANT: {instruments_str} must be prominent and audible throughout the entire track, starting from second 0. Vocals in {language}. Professional studio production quality.")
        
        prompt = " ".join([part for part in prompt_parts if part])
        
        if request.tempo < 90:
            prompt += f" Slow tempo at {request.tempo} BPM with deliberate pacing."
        elif request.tempo > 140:
            prompt += f" Fast tempo at {request.tempo} BPM with energetic rhythm."
        else:
            prompt += f" Moderate tempo at {request.tempo} BPM with steady groove."
        
        return prompt, language
    
    async def _generate_complete_song(self, prompt: str, lyrics: str, duration_ms: int, language_name: str) -> bytes:
        """Generate complete song using ElevenLabs Music API (compose_detailed)"""
        try:
            lyrics_clean = (lyrics or "").strip()
            if lyrics_clean and len(lyrics_clean) > 2000:
                # Trim without cutting in middle of word
                truncated = lyrics_clean[:2000]
                last_newline = truncated.rfind("\n")
                if last_newline > 1500:
                    lyrics_clean = truncated[:last_newline] + "\n..."
                else:
                    lyrics_clean = truncated + "..."
            
            if lyrics_clean:
                full_prompt = (
                    f"{prompt}\n\n"
                    f"INSTRUMENTAL REQUIREMENT: All specified instruments MUST start playing from the very first second (0:00) of the track. "
                    f"Create a 2-4 second musical intro with the instruments before vocals begin. "
                    f"Then sing the following lyrics exactly as written in {language_name}, with instruments continuing throughout:\n\n"
                    f"{lyrics_clean}\n\n"
                    f"Remember: Instruments play from 0:00, vocals start after brief instrumental intro, both continue together until the end."
                )
            else:
                full_prompt = (
                    f"{prompt}\n\n"
                    f"No lyrics provided. Create an instrumental track where all specified instruments play from second 0 throughout the entire duration. "
                    f"Add simple melodic vocals with open syllables (la, oh, ah) in {language_name}."
                )
            
            # Use compose_detailed to get audio + metadata (including AI-generated lyrics if needed)
            # NOTE: compose_detailed is ASYNC, so we await it directly!
            result = await asyncio.wait_for(
                self.client.music.compose_detailed(
                    prompt=full_prompt,
                    music_length_ms=duration_ms,  # Use requested duration
                    model_id="music_v1"
                ),
                timeout=120.0  # 2 dakika timeout
            )
            
            # result.audio contains the MP3 bytes
            # result.json contains composition_plan with sections, lyrics, etc.
            return result.audio
            
        except PromptSafetyError:
            raise
        except Exception as e:
            prompt_error = self._extract_prompt_safety_error(e)
            if prompt_error:
                raise PromptSafetyError(
                    prompt_error["message"],
                    suggestion=prompt_error.get("suggestion"),
                    detail=prompt_error.get("detail"),
                ) from e
            raise Exception(f"ElevenLabs Music API error: {str(e)}")


    async def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get available music generation models"""
        # For music generation, return empty list
        return []

    async def clone_voice(self, name: str, description: str, files: List[bytes]) -> Dict[str, Any]:
        """Clone a voice using provided audio samples"""
        raise Exception("Voice cloning not supported in this version")

    async def enhance_audio(self, audio_path: str, enhancement_type: str = "music") -> str:
        """Enhance audio quality and add background music"""
        try:
            # This would integrate with additional audio processing
            # For now, return the original path
            # In production, you'd use tools like:
            # - FFmpeg for audio processing
            # - Background music libraries
            # - Audio enhancement APIs
            
            return audio_path
            
        except Exception as e:
            raise Exception(f"Error enhancing audio: {str(e)}")

    def _extract_prompt_safety_error(self, err: Exception) -> Optional[Dict[str, Any]]:
        """Try to read ElevenLabs prompt safety metadata from the exception."""
        status_code = getattr(err, "status_code", None)
        response = getattr(err, "response", None)
        if not status_code and response is not None:
            status_code = getattr(response, "status_code", None)

        error_text = str(err)
        if status_code != 400 and "status_code: 400" not in error_text:
            return None

        body = getattr(err, "body", None)
        if body is None and response is not None:
            try:
                body = response.json()
            except Exception:
                try:
                    body = response.text
                except Exception:
                    body = None

        detail_dict = self._coerce_detail_dict(body)
        if not detail_dict:
            detail_dict = self._coerce_detail_dict_from_text(error_text)

        if not isinstance(detail_dict, dict):
            return None

        status = detail_dict.get("status") or detail_dict.get("code")
        if status not in {"bad_prompt", "prompt_safety", "BAD_PROMPT"}:
            return None

        suggestion = (
            detail_dict.get("promptSuggestion")
            or detail_dict.get("prompt_suggestion")
        )
        if not suggestion:
            data = detail_dict.get("data")
            if isinstance(data, dict):
                suggestion = data.get("prompt_suggestion")

        message = detail_dict.get("message") or "Prompt rejected by ElevenLabs safety rules."
        return {
            "message": message,
            "suggestion": suggestion,
            "detail": detail_dict,
        }

    def _coerce_detail_dict(self, payload: Any) -> Optional[Dict[str, Any]]:
        """Normalize various payload shapes into a dictionary."""
        if not payload:
            return None

        if isinstance(payload, dict):
            detail = payload.get("detail")
            if isinstance(detail, dict) and detail:
                return detail
            return payload

        if isinstance(payload, (bytes, bytearray)):
            payload = payload.decode("utf-8", errors="ignore")

        if isinstance(payload, str):
            payload = payload.strip()
            parsed = self._safe_parse_string_dict(payload)
            if isinstance(parsed, dict):
                detail = parsed.get("detail")
                if isinstance(detail, dict):
                    return detail
                return parsed

        return None

    def _coerce_detail_dict_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Best-effort parser for ElevenLabs error text that embeds Python dicts."""
        if not text or "body:" not in text:
            return None

        fragment = text.split("body:", 1)[1].strip()
        if not fragment:
            return None

        parsed = self._safe_parse_string_dict(fragment)
        if isinstance(parsed, dict):
            detail = parsed.get("detail")
            if isinstance(detail, dict):
                return detail
            return parsed

        return None

    @staticmethod
    def _safe_parse_string_dict(value: str) -> Optional[Dict[str, Any]]:
        """Parse a string that may contain JSON or Python dict literals."""
        if not value:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            try:
                return ast.literal_eval(value)
            except (ValueError, SyntaxError):
                return None

# Singleton instance
elevenlabs_service = ElevenLabsService()

__all__ = ["elevenlabs_service", "PromptSafetyError"]
