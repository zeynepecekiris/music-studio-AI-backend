"""
Stem separation for the in-app mixer, through ElevenLabs Music
(POST /v1/music/stem-separation → a ZIP with one audio file per stem).

It can take longer than Heroku's 30 s request limit, so it runs on a
background thread; the app polls GET /songs/{id}/stems until it's ready.
"""
import asyncio
import io
import logging
import os
import threading
import zipfile

import httpx

from config.settings import settings
from db.base import SessionLocal
from db.models import Song
from services.storage_service import upload_file

log = logging.getLogger(__name__)

URL = "https://api.elevenlabs.io/v1/music/stem-separation"
# File names in the ZIP → our channel names (first match wins)
KINDS = [("vocal", "vocals"), ("drum", "drums"), ("bass", "bass"),
         ("guitar", "guitar"), ("piano", "piano"), ("other", "other"),
         ("instrument", "other"), ("accompan", "other")]
ORDER = ["vocals", "drums", "bass", "guitar", "piano", "other"]


def _kind(name: str) -> str:
    low = os.path.basename(name).lower()
    for key, kind in KINDS:
        if key in low:
            return kind
    return os.path.splitext(os.path.basename(name))[0].lower()[:20] or "other"


def start(song_id: str) -> None:
    threading.Thread(target=_run, args=(song_id,), daemon=True).start()


def _audio_bytes(url: str) -> bytes:
    if url.startswith("/"):  # local dev storage
        with open(os.path.join(settings.UPLOAD_DIR, url.lstrip("/")), "rb") as f:
            return f.read()
    with httpx.Client(timeout=60, follow_redirects=True) as c:
        r = c.get(url)
        r.raise_for_status()
        return r.content


def _separate(audio: bytes) -> dict:
    with httpx.Client(timeout=300) as c:
        r = c.post(
            URL,
            params={"output_format": "mp3_44100_128"},
            headers={"xi-api-key": settings.ELEVENLABS_API_KEY},
            files={"file": ("song.mp3", audio, "audio/mpeg")},
        )
        if r.status_code >= 400:
            raise RuntimeError(f"ElevenLabs {r.status_code}: {r.text[:300]}")
    out = {}
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        for name in z.namelist():
            if name.endswith("/") or not name.lower().endswith((".mp3", ".wav")):
                continue
            kind = _kind(name)
            if kind in out:  # e.g. two "other" files: keep both
                kind = f"{kind}{len(out)}"
            out[kind] = (z.read(name), os.path.splitext(name)[1].lower())
    if not out:
        raise RuntimeError("no stems in response")
    return out


def _run(song_id: str) -> None:
    db = SessionLocal()
    try:
        song = db.query(Song).filter(Song.id == song_id).first()
        if not song:
            return
        stems = _separate(_audio_bytes(song.audio_url))
        urls = {}
        for kind, (data, ext) in stems.items():
            ctype = "audio/mpeg" if ext == ".mp3" else "audio/wav"
            urls[kind] = asyncio.run(upload_file(data, f"stems/{song_id}", f"{kind}{ext}", ctype))
        song.stems = {k: urls[k] for k in sorted(urls, key=lambda k: ORDER.index(k) if k in ORDER else 99)}
        song.stems_status = "ready"
        db.commit()
    except Exception:
        log.exception("stems: separation failed for %s", song_id)
        db.rollback()
        song = db.query(Song).filter(Song.id == song_id).first()
        if song:
            song.stems_status = "failed"
            db.commit()
    finally:
        db.close()
