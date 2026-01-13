from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid
from datetime import datetime

class MusicTheme(str, Enum):
    LOVE = "love"
    FRIENDSHIP = "friendship"
    HEARTBREAK = "heartbreak"
    HAPPINESS = "happiness"
    SADNESS = "sadness"
    CELEBRATION = "celebration"
    COUNTRY = "country"
    NOSTALGIA = "nostalgia"
    HOPE = "hope"
    FAMILY = "family"
    ADVENTURE = "adventure"
    MOTIVATION = "motivation"
    PEACE = "peace"

class MusicGenre(str, Enum):
    POP = "pop"
    ROCK = "rock"
    JAZZ = "jazz"
    BLUES = "blues"
    CLASSICAL = "classical"
    ELECTRONIC = "electronic"
    ACOUSTIC = "acoustic"
    RAP = "rap"
    FOLK = "folk"
    METAL = "metal"
    COUNTRY = "country"
    RNB = "rnb"
    REGGAE = "reggae"
    # New genres
    HOUSE = "house"
    TECHNO = "techno"
    TRANCE = "trance"
    DRUM_AND_BASS = "drum_and_bass"
    DREAM_POP = "dream_pop"
    TRIP_HOP = "trip_hop"
    CHILLWAVE = "chillwave"
    OPERA = "opera"
    SYMPHONIC = "symphonic"
    K_POP = "k_pop"
    J_POP = "j_pop"
    C_POP = "c_pop"
    BOLLYWOOD = "bollywood"
    LATIN = "latin"
    FLAMENCO = "flamenco"
    DISCO = "disco"
    DANCEHALL = "dancehall"
    HIP_HOP = "hip_hop"
    TRAP = "trap"

class VoiceGender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"
    INSTRUMENTAL = "instrumental"

class MusicMood(str, Enum):
    HAPPY = "happy"
    SAD = "sad"
    ROMANTIC = "romantic"
    ENERGETIC = "energetic"
    CALM = "calm"
    NOSTALGIC = "nostalgic"
    MELANCHOLIC = "melancholic"
    UPBEAT = "upbeat"
    RELAXED = "relaxed"
    DARK = "dark"
    DREAMY = "dreamy"

class Instrument(str, Enum):
    PIANO = "piano"
    GUITAR = "guitar"
    VIOLIN = "violin"
    DRUMS = "drums"
    SAXOPHONE = "saxophone"
    FLUTE = "flute"
    SYNTHESIZER = "synthesizer"
    ACOUSTIC_GUITAR = "acoustic_guitar"
    ELECTRIC_GUITAR = "electric_guitar"
    BASS = "bass"
    BASS_GUITAR = "bass_guitar"
    TRUMPET = "trumpet"
    CELLO = "cello"
    KEYBOARD = "keyboard"
    HARP = "harp"

# Request Models
class LyricsGenerationRequest(BaseModel):
    story: str = Field(..., min_length=10, max_length=2000, description="User's story")
    theme: MusicTheme = Field(..., description="Music theme")
    user_id: Optional[str] = Field(None, description="User ID for tracking")
    language: str = Field("tr", description="Language code (tr, en, es)")

class MusicGenerationRequest(BaseModel):
    lyrics: Optional[str] = Field(None, description="Generated lyrics (optional for instrumental)")
    story: str = Field(..., description="Original story")
    theme: MusicTheme = Field(..., description="Music theme")
    genre: MusicGenre = Field(MusicGenre.POP, description="Music genre")
    voice_gender: VoiceGender = Field(VoiceGender.FEMALE, description="Voice gender")
    mood: MusicMood = Field(MusicMood.HAPPY, description="Music mood")
    instruments: List[Instrument] = Field(default=[Instrument.PIANO], description="Selected instruments")
    tempo: int = Field(120, ge=60, le=200, description="Tempo (BPM)")
    duration: int = Field(30, ge=15, le=300, description="Duration in seconds (15-300 seconds)")
    language: str = Field("tr", description="Language code (tr, en, es)")
    user_id: Optional[str] = Field(None, description="User ID for tracking")

# Response Models
class LyricsResponse(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    lyrics: str
    theme: MusicTheme
    language: str
    created_at: datetime = Field(default_factory=datetime.now)
    processing_time: float
    word_count: int

class MusicGenerationResponse(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    audio_url: str
    lyrics: Optional[str] = None
    story: str
    theme: MusicTheme
    genre: MusicGenre
    voice_gender: VoiceGender
    mood: MusicMood
    instruments: List[Instrument]
    tempo: int
    duration: int
    created_at: datetime = Field(default_factory=datetime.now)
    processing_time: float
    file_size: Optional[int] = None

class AudioProcessingStatus(BaseModel):
    task_id: str
    status: str  # pending, processing, completed, failed
    progress: int = Field(0, ge=0, le=100)
    estimated_completion: Optional[datetime] = None
    error_message: Optional[str] = None

# User Models
class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: Optional[str] = Field(None, pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    language: str = Field("tr", description="Preferred language")

class UserResponse(BaseModel):
    id: str
    name: str
    email: Optional[str]
    language: str
    created_at: datetime
    total_lyrics_generated: int = 0
    total_music_generated: int = 0

# Music History Models
class MusicHistoryItem(BaseModel):
    id: str
    title: str
    theme: MusicTheme
    genre: MusicGenre
    audio_url: str
    lyrics_preview: str = Field(..., max_length=200)
    created_at: datetime
    duration: int
    is_favorite: bool = False

class MusicHistoryResponse(BaseModel):
    items: List[MusicHistoryItem]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool

# Error Models
class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)

# Health Check
class HealthCheck(BaseModel):
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = "1.0.0"
    services: Dict[str, str] = Field(default_factory=dict)

# Analytics
class AnalyticsResponse(BaseModel):
    total_lyrics_generated: int
    total_music_generated: int
    popular_themes: List[Dict[str, Any]]
    popular_genres: List[Dict[str, Any]]
    average_processing_time: float
    success_rate: float
