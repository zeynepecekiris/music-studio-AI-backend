"""
Pure mapping functions: high-level config → ElevenLabs API payload.
Turkish: Config'i ElevenLabs API formatına dönüştüren pure fonksiyonlar.
"""
from typing import Optional
from app.models import GenerateConfig, ElevenLabsPayload


# === MAPPING DICTIONARIES ===

GENRE_MAP = {
    "pop": "pop",
    "rnb": "rnb",
    "trap": "trap",
    "edm": "edm",
    "indie": "indie",
    "lofi": "lofi",
    "synthwave": "synthwave",
    "cinematic": "cinematic",
    "world": "world",
    "reggaeton": "reggaeton",
    "rock": "rock",
    "folk": "folk",
    "jazz": "jazz",
    "classical": "classical",
    "hiphop": "hiphop",
    "blues": "blues",
    "country": "country",
    "metal": "metal",
}

FUSION_TAGS = {
    "turkish_makam": "anatolian_flavor",
    "synthwave": "synthwave",
    "afrobeat": "afrobeat",
    "latin": "latin_fusion",
    "oriental": "oriental_fusion",
}

# Instrument preset combinations (lead, support tuple) -> preset name
INSTRUMENT_PRESET_MAP: dict[tuple[str, ...], str] = {
    ("piano", "pad", "808"): "piano_pad_pop",
    ("piano", "strings"): "piano_strings_cinematic",
    ("guitar", "pad"): "guitar_ambient",
    ("baglama",): "anatolian_pop",
    ("baglama", "davul", "ney"): "turkish_traditional",
    ("synth", "bass", "drums"): "synth_pop",
    ("guitar", "bass", "drums"): "rock_standard",
    ("piano", "violin"): "classical_duet",
    ("808", "hi_hat", "clap"): "trap_minimal",
}

# Voice preset mapping (gender, register, persona) -> preset name
VOICE_PRESET_MAP: dict[tuple[str, str, Optional[str]], str] = {
    ("female", "airy", "duet"): "female_soft_airy_duet",
    ("female", "airy", None): "female_soft_airy",
    ("female", "chesty", None): "female_chest_pop",
    ("female", "powerful", None): "female_powerful_belt",
    ("female", "breathy", None): "female_breathy_intimate",
    ("female", "soft", None): "female_soft_ballad",
    ("male", "airy", None): "male_soft_airy",
    ("male", "chesty", None): "male_chest_pop",
    ("male", "powerful", None): "male_powerful_rock",
    ("male", "breathy", None): "male_breathy_rnb",
    ("male", "soft", None): "male_soft_folk",
    ("duet", "airy", None): "duet_soft_airy",
    ("duet", "chesty", None): "duet_balanced",
    ("nonbinary", "airy", None): "androgynous_airy",
}


# === HELPER FUNCTIONS ===

def to_key_signature(key: str, scale: str) -> str:
    """
    Tonalite + skala → 'C major', 'A minor' formatı.
    
    Args:
        key: "C", "D#", "Bb" gibi notalar
        scale: "major", "minor", "dorian" vb.
    
    Returns:
        "C major" formatında string
    """
    return f"{key} {scale}"


def build_lyrics_prompt(cfg: GenerateConfig) -> str:
    """
    Tema, alt tema, keywords, persona'dan lyrics prompt oluştur.
    
    Turkish: Şarkı sözü prompt'unu config'den oluştur.
    
    Args:
        cfg: Kullanıcı config'i
    
    Returns:
        ElevenLabs için lyrics prompt string
    """
    parts = []
    
    # Ana tema
    parts.append(f"Theme: {cfg.theme}")
    
    # Alt tema varsa
    if cfg.subtheme:
        parts.append(f"Subtheme: {cfg.subtheme}")
    
    # Persona varsa
    if cfg.persona:
        parts.append(f"Persona: {cfg.persona}")
    
    # Keywords varsa
    if cfg.lyrics.keywords:
        keywords_str = ", ".join(cfg.lyrics.keywords)
        parts.append(f"Keywords: {keywords_str}")
    
    # Stil bilgisi
    parts.append(f"Style: {cfg.lyrics.style}")
    parts.append(f"Rhyme: {cfg.lyrics.rhyme_scheme}")
    
    # Dil bilgisi
    lang_str = ", ".join(cfg.language)
    parts.append(f"Language: {lang_str}")
    
    return " | ".join(parts)


def choose_instrument_preset(cfg: GenerateConfig) -> str:
    """
    Enstrümantasyon config'inden preset seç veya compose et.
    
    Turkish: Enstrüman ayarlarından preset string oluştur.
    
    Args:
        cfg: Kullanıcı config'i
    
    Returns:
        Instrument preset string
    """
    inst = cfg.instrumentation
    
    # Lead + support instruments tuple oluştur
    key_tuple = tuple([inst.lead_instrument] + sorted(inst.support_instruments))
    
    # Exact match varsa kullan
    if key_tuple in INSTRUMENT_PRESET_MAP:
        return INSTRUMENT_PRESET_MAP[key_tuple]
    
    # Sadece lead instrument
    lead_only = (inst.lead_instrument,)
    if lead_only in INSTRUMENT_PRESET_MAP:
        return INSTRUMENT_PRESET_MAP[lead_only]
    
    # Fallback: compose name
    support_str = "_".join(sorted(inst.support_instruments)[:2]) if inst.support_instruments else "solo"
    return f"{inst.lead_instrument}_{support_str}_{cfg.music.genre}"


def choose_voice_preset(cfg: GenerateConfig) -> str:
    """
    Vokal config'inden preset seç.
    
    Turkish: Vokal ayarlarından preset string oluştur.
    
    Args:
        cfg: Kullanıcı config'i
    
    Returns:
        Voice preset string
    """
    vocal = cfg.vocal
    
    # Persona'yı gender olarak kullan (duet ise)
    gender = cfg.persona if cfg.persona == "duet" else vocal.vocal_gender
    register = vocal.vocal_register
    persona = cfg.persona if cfg.persona != "duet" else None
    
    # Lookup key
    key = (gender, register, persona)
    
    # Exact match
    if key in VOICE_PRESET_MAP:
        return VOICE_PRESET_MAP[key]
    
    # Fallback: persona olmadan
    fallback_key = (gender, register, None)
    if fallback_key in VOICE_PRESET_MAP:
        return VOICE_PRESET_MAP[fallback_key]
    
    # Son fallback: compose name
    return f"{gender}_{register}_{cfg.music.genre}"


def merge_genre_fusion(genre: str, fusion: list[str]) -> str:
    """
    Ana tür + fusion türleri birleştir.
    
    Turkish: Ana tür ve fusion türlerini birleştir.
    
    Args:
        genre: Ana tür
        fusion: Fusion tür listesi
    
    Returns:
        Birleştirilmiş genre string
    """
    base = GENRE_MAP.get(genre, genre)
    
    if not fusion:
        return base
    
    # Fusion tags'i map et
    fusion_tags = [FUSION_TAGS.get(f, f) for f in fusion]
    
    # Birleştir
    return f"{base}_" + "_".join(fusion_tags[:2])  # Max 2 fusion tag


# === MAIN MAPPING FUNCTION ===

def map_to_music_api(cfg: GenerateConfig) -> ElevenLabsPayload:
    """
    Ana mapping fonksiyonu: GenerateConfig → ElevenLabsPayload.
    Pure function, side-effect yok.
    
    Turkish: Config'i ElevenLabs API payload'una dönüştür.
    
    Args:
        cfg: Kullanıcı config'i
    
    Returns:
        ElevenLabs API için payload
    """
    return ElevenLabsPayload(
        # Lyrics prompt
        lyrics_prompt=build_lyrics_prompt(cfg),
        
        # Music basics
        genre=merge_genre_fusion(cfg.music.genre, cfg.music.fusion),
        bpm=cfg.music.bpm,
        key_signature=to_key_signature(cfg.music.key, cfg.music.scale),
        time_signature=cfg.music.time_signature,
        duration_seconds=cfg.structure.duration_sec,
        
        # Voice & instruments
        voice=choose_voice_preset(cfg),
        instrument_preset=choose_instrument_preset(cfg),
        hooks=cfg.instrumentation.hooks,
        
        # Production
        mixing={
            "tape_sat": cfg.production.mix_bus.tape_sat,
            "glue_comp": cfg.production.mix_bus.glue_comp,
        },
        vocals_fx=cfg.production.vocals_fx,
        mastering={
            "target_lufs": cfg.production.mastering.target_lufs,
            "stereo_width": cfg.production.mastering.stereo_width,
            "limiter": cfg.production.mastering.limiter,
        },
        
        # Stems & FX
        stems=cfg.structure.stems,
        fx_sfx=cfg.production.fx_sfx,
        
        # AI params
        seed=cfg.ai.seed,
        creativity=cfg.ai.creativity,
        guidance=cfg.ai.guidance,
        repetition_penalty=cfg.ai.repetition_penalty,
        
        # Safety
        safety={
            "explicit_ok": cfg.explicit_ok,
        },
    )

