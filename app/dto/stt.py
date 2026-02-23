"""
DTOs for STT (speech-to-text) provider calls.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class STTRequestDTO(BaseModel):
    request_id: UUID
    provider: str = "assemblyai"
    audio_source: str = "telegram"        # where the audio came from
    audio_url: Optional[str] = None       # direct URL
    audio_bytes: Optional[bytes] = None   # raw bytes (excluded from serialisation)
    language: str = "ru"

    class Config:
        # bytes are not JSON-serialisable by default
        json_encoders = {bytes: lambda v: f"<{len(v)} bytes>"}


class STTResultDTO(BaseModel):
    request_id: UUID
    provider: str = "assemblyai"
    transcript_text: str = ""
    duration_seconds: Optional[float] = None
    provider_job_id: Optional[str] = None
    status: str = "ok"                    # ok | error
    error_code: Optional[str] = None
    error_message: Optional[str] = None
