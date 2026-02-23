"""
Abstract base for LLM providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.dto.llm import LLMRequestDTO, LLMResultDTO


class BaseLLMProvider(ABC):
    """Interface all LLM providers must implement."""

    @abstractmethod
    async def generate(self, request: LLMRequestDTO) -> LLMResultDTO:
        ...
