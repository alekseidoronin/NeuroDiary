"""
DTOs for Telegram input normalisation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class InputNormalizedDTO(BaseModel):
    """Normalised input after parsing the Telegram update."""
    request_id: UUID = Field(default_factory=uuid4)
    tg_user_id: int
    chat_id: int
    message_id: int
    input_type: str                      # "voice" | "audio" | "text"
    telegram_file_id: Optional[str] = None
    raw_text: Optional[str] = None       # present if input_type == "text"
    voice_duration: Optional[int] = None # seconds
    received_at: datetime = Field(default_factory=datetime.utcnow)
    locale: str = "ru"
    timezone: str = "Asia/Dubai"
    username: Optional[str] = None
    first_name: Optional[str] = None
