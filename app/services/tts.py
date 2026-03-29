"""
TTS service based on gTTS with local cache.
"""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path

from gtts import gTTS

logger = logging.getLogger(__name__)

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_SPACES_RE = re.compile(r"\s+")
_CACHE_DIR = Path("/tmp/diary_tts_cache")
_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def normalize_for_tts(text: str, max_len: int = 3500) -> str:
    plain = _HTML_TAG_RE.sub(" ", text or "")
    plain = _SPACES_RE.sub(" ", plain).strip()
    if len(plain) > max_len:
        plain = plain[: max_len - 3] + "..."
    return plain


def _cache_path(text: str, lang: str) -> Path:
    digest = hashlib.sha256(f"{lang}:{text}".encode("utf-8")).hexdigest()
    return _CACHE_DIR / f"{digest}.mp3"


def _pick_voice(locale: str) -> str:
    # Keep Russian as default app language for voice output.
    return "ru"


async def synthesize(text: str, locale: str = "ru") -> bytes:
    prepared = normalize_for_tts(text)
    if not prepared:
        raise ValueError("Empty text after normalization")

    cache_file = _cache_path(prepared, locale)
    if cache_file.exists():
        return cache_file.read_bytes()

    lang = _pick_voice(locale)

    logger.info("TTS synth start: chars=%s locale=%s", len(prepared), locale)
    tts = gTTS(text=prepared, lang=lang, slow=False)
    tts.save(str(cache_file))
    audio_bytes = cache_file.read_bytes()
    return audio_bytes
