"""
Abstract base for STT providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.dto.stt import STTRequestDTO, STTResultDTO


class BaseSTTProvider(ABC):
    """Interface all STT providers must implement."""

    @abstractmethod
    async def transcribe(self, request: STTRequestDTO) -> STTResultDTO:
        ...
