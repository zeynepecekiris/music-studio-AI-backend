"""International profile fields, shared by every endpoint that returns a user."""
import unicodedata
from typing import Optional

# Letters that don't decompose into base + accent
_FOLD = str.maketrans({"İ": "i", "I": "i", "ı": "i", "ß": "ss", "ø": "o", "Ø": "o", "æ": "ae", "Æ": "ae", "ł": "l", "Ł": "l", "đ": "d"})


def city_key(city: Optional[str]) -> Optional[str]:
    """Fold a city name for matching: case, accents and the Turkish dotted/dotless i."""
    if not city:
        return None
    s = unicodedata.normalize("NFKD", city.translate(_FOLD))
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    s = " ".join(s.replace("-", " ").split())
    return s[:60] or None


def world_fields(user) -> dict:
    return {
        "country_code": user.country_code,
        "city": user.city,
        "visited_countries": list(user.visited_countries or []),
        "languages": list(user.languages or []),
    }
