"""
Feature flags and plan limits validation.
Turkish: Plan limitleri ve validasyon.
"""
from typing import Literal
from fastapi import HTTPException
from app.models import GenerateConfig


PlanType = Literal["free", "pro", "studio", "label"]


# Plan limitleri
PLAN_LIMITS = {
    "free": {
        "max_duration": 90,
        "allowed_stems": ["master"],
        "mastering_controls": False,
        "max_creativity": 0.5,
        "batch_allowed": False,
    },
    "pro": {
        "max_duration": 150,
        "allowed_stems": ["master", "vocals", "instrumental"],
        "mastering_controls": False,
        "max_creativity": 0.75,
        "batch_allowed": False,
    },
    "studio": {
        "max_duration": 210,
        "allowed_stems": ["master", "vocals", "drums", "bass", "instruments", "fx"],
        "mastering_controls": True,
        "max_creativity": 1.0,
        "batch_allowed": False,
    },
    "label": {
        "max_duration": 300,
        "allowed_stems": ["master", "vocals", "drums", "bass", "instruments", "fx", "midi"],
        "mastering_controls": True,
        "max_creativity": 1.0,
        "batch_allowed": True,
    },
}


def validate_plan_limits(cfg: GenerateConfig, plan: PlanType = "free") -> None:
    """
    Plan limitlerini kontrol et, ihlal varsa HTTP 400 raise et.
    
    Turkish: Kullanıcı planına göre limitleri kontrol et.
    
    Args:
        cfg: Kullanıcı config'i
        plan: Kullanıcı planı (free/pro/studio/label)
    
    Raises:
        HTTPException: Plan limitleri ihlal edilirse 400 hatası
    """
    limits = PLAN_LIMITS[plan]
    
    # Duration check
    if cfg.structure.duration_sec > limits["max_duration"]:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Duration {cfg.structure.duration_sec}s exceeds {plan} plan limit "
                f"of {limits['max_duration']}s. Upgrade to use longer durations."
            ),
        )
    
    # Stems check
    invalid_stems = set(cfg.structure.stems) - set(limits["allowed_stems"])
    if invalid_stems:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Stems {invalid_stems} not allowed in {plan} plan. "
                f"Allowed stems: {limits['allowed_stems']}. Upgrade for more stems."
            ),
        )
    
    # Mastering controls check
    if not limits["mastering_controls"]:
        default_lufs = -14
        default_width = 60
        default_limiter = "balanced"
        
        if (
            cfg.production.mastering.target_lufs != default_lufs
            or cfg.production.mastering.stereo_width != default_width
            or cfg.production.mastering.limiter != default_limiter
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Mastering controls not available in {plan} plan. "
                    f"Upgrade to studio or label plan for custom mastering."
                ),
            )
    
    # Creativity check
    if cfg.ai.creativity > limits["max_creativity"]:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Creativity {cfg.ai.creativity} exceeds {plan} plan limit "
                f"of {limits['max_creativity']}. Upgrade for higher creativity."
            ),
        )


def get_plan_info(plan: PlanType) -> dict:
    """
    Plan bilgilerini döndür.
    
    Turkish: Plan detaylarını getir.
    
    Args:
        plan: Plan tipi
    
    Returns:
        Plan limitleri dict'i
    """
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

