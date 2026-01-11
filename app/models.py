"""
Pydantic models for high-level music generation config.
Turkish: Müzik üretimi için yüksek seviye config modelleri.
"""
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator


class LyricsConfig(BaseModel):
    """Şarkı sözü konfigürasyonu"""
    style: Literal["poetic", "conversational", "narrative", "abstract"] = "poetic"
    rhyme_scheme: str = Field(default="ABAB", pattern="^[A-Z]+$")
    syllable_density: Literal["low", "med", "high"] = "med"
    keywords: list[str] = Field(default_factory=list)


class MusicConfig(BaseModel):
    """Müzik teorisi ve stil konfigürasyonu"""
    genre: str = Field(..., description="Ana tür")
    fusion: list[str] = Field(default_factory=list, description="Fusion türler")
    bpm: int = Field(default=120, ge=40, le=200)
    key: str = Field(default="C", pattern="^[A-G](#|b)?$")
    scale: Literal["major", "minor", "dorian", "phrygian", "lydian", "mixolydian"] = "major"
    time_signature: str = Field(default="4/4", pattern=r"^\d+/\d+$")
    tempo_curve: Literal["steady", "build", "drop", "dynamic"] = "steady"
    chord_palette: Literal["diatonic", "extended", "modal", "chromatic"] = "diatonic"


class InstrumentationConfig(BaseModel):
    """Enstrümantasyon konfigürasyonu"""
    lead_instrument: str = "piano"
    support_instruments: list[str] = Field(default_factory=list)
    percussion_style: str = "acoustic"
    hooks: list[str] = Field(default_factory=list)


class VocalConfig(BaseModel):
    """Vokal konfigürasyonu"""
    vocal_gender: Literal["female", "male", "nonbinary", "duet"] = "female"
    vocal_register: Literal["airy", "chesty", "breathy", "powerful", "soft"] = "airy"
    multilayer: list[str] = Field(default_factory=list)
    language_split: dict[str, int] = Field(default_factory=lambda: {"tr": 100})
    
    @field_validator("language_split")
    @classmethod
    def validate_language_split(cls, v: dict[str, int]) -> dict[str, int]:
        total = sum(v.values())
        if total != 100:
            raise ValueError(f"Language split must sum to 100, got {total}")
        return v


class StructureConfig(BaseModel):
    """Şarkı yapısı konfigürasyonu"""
    form: list[str] = Field(
        default_factory=lambda: ["intro", "v1", "ch", "v2", "ch", "bridge", "ch", "outro"]
    )
    drop_type: Optional[str] = None
    duration_sec: int = Field(default=150, ge=30, le=300)
    stems: list[str] = Field(
        default_factory=lambda: ["master"],
        description="Stem track'ler"
    )


class MixBusConfig(BaseModel):
    """Mix bus ayarları"""
    glue_comp: Literal["off", "light", "med", "heavy"] = "light"
    tape_sat: bool = False


class MasteringConfig(BaseModel):
    """Mastering ayarları"""
    target_lufs: int = Field(default=-14, ge=-20, le=-6)
    stereo_width: int = Field(default=60, ge=0, le=100)
    limiter: Literal["transparent", "balanced", "brick"] = "balanced"


class ProductionConfig(BaseModel):
    """Production ve mixing ayarları"""
    mix_bus: MixBusConfig = Field(default_factory=MixBusConfig)
    vocals_fx: list[str] = Field(default_factory=list)
    mastering: MasteringConfig = Field(default_factory=MasteringConfig)
    fx_sfx: list[str] = Field(default_factory=list)


class AIConfig(BaseModel):
    """AI generation parametreleri"""
    seed: Optional[int] = None
    creativity: float = Field(default=0.5, ge=0.0, le=1.0)
    guidance: float = Field(default=7.5, ge=1.0, le=20.0)
    repetition_penalty: float = Field(default=1.0, ge=0.0, le=2.0)


class GenerateConfig(BaseModel):
    """Ana config modeli - kullanıcıdan gelen tam config"""
    theme: str = Field(..., description="Ana tema (örn: love, loss, celebration)")
    subtheme: Optional[str] = Field(None, description="Alt tema (örn: long_distance, heartbreak)")
    language: list[str] = Field(default_factory=lambda: ["tr"])
    persona: Optional[str] = Field(None, description="Şarkıcı karakteri (örn: duet, storyteller)")
    explicit_ok: bool = False
    lyrics: LyricsConfig = Field(default_factory=LyricsConfig)
    music: MusicConfig
    instrumentation: InstrumentationConfig = Field(default_factory=InstrumentationConfig)
    vocal: VocalConfig = Field(default_factory=VocalConfig)
    structure: StructureConfig = Field(default_factory=StructureConfig)
    production: ProductionConfig = Field(default_factory=ProductionConfig)
    ai: AIConfig = Field(default_factory=AIConfig)


class ElevenLabsPayload(BaseModel):
    """ElevenLabs API'ye gönderilecek payload"""
    lyrics_prompt: str
    genre: str
    bpm: int
    key_signature: str
    time_signature: str
    duration_seconds: int
    voice: str
    instrument_preset: str
    hooks: list[str]
    mixing: dict
    vocals_fx: list[str]
    mastering: dict
    stems: list[str]
    fx_sfx: list[str]
    seed: Optional[int]
    creativity: float
    guidance: float
    repetition_penalty: float
    safety: dict


class GenerateResponse(BaseModel):
    """API response modeli"""
    status: Literal["ok", "error"]
    url_master: str
    stems: dict[str, str] = Field(default_factory=dict)
    meta: dict

