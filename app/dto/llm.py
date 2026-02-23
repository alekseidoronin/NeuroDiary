"""
DTOs for LLM provider calls (Gemini / OpenAI).
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel


class LLMRequestDTO(BaseModel):
    request_id: UUID
    provider: str                          # "gemini" | "openai"
    model: str
    system_prompt: str
    user_prompt: str
    variables: Dict[str, Any] = {}
    temperature: float = 0.7
    max_tokens: int = 4096


class LLMResultDTO(BaseModel):
    request_id: UUID
    provider: str
    model: str = ""
    final_text: str = ""
    status: str = "ok"                     # ok | error
    tokens_in: int = 0
    tokens_out: int = 0
    error_code: Optional[str] = None
    error_message: Optional[str] = None
