"""
OpenAI ChatGPT LLM provider.
"""

from __future__ import annotations

import logging

from openai import AsyncOpenAI

from app.config import settings
from app.dto.llm import LLMRequestDTO, LLMResultDTO
from app.services.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str = "", model: str = ""):
        self._api_key = api_key or settings.OPENAI_API_KEY
        self._model = model or settings.OPENAI_MODEL
        self._client = AsyncOpenAI(api_key=self._api_key)

    async def generate(self, request: LLMRequestDTO) -> LLMResultDTO:
        logger.info("OpenAI: generating for request %s (model=%s)", request.request_id, self._model)

        import os
        original_key = os.environ.get("OPENAI_API_KEY")
        if self._api_key:
            os.environ["OPENAI_API_KEY"] = self._api_key

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": request.system_prompt},
                    {"role": "user", "content": request.user_prompt},
                ],
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
            
            text = response.choices[0].message.content or ""
            usage = response.usage

            tokens_in = usage.prompt_tokens if usage else 0
            tokens_out = usage.completion_tokens if usage else 0

            logger.info("OpenAI: response %d tokens_in, %d tokens_out", tokens_in, tokens_out)

            return LLMResultDTO(
                request_id=request.request_id,
                provider="openai",
                model=self._model,
                final_text=text.strip(),
                status="ok",
                tokens_in=tokens_in,
                tokens_out=tokens_out,
            )

        except Exception as e:
            logger.exception("OpenAI generation failed")
            return LLMResultDTO(
                request_id=request.request_id,
                provider="openai",
                model=self._model,
                status="error",
                error_code="openai_error",
                error_message=str(e),
            )
        finally:
            if original_key is not None:
                os.environ["OPENAI_API_KEY"] = original_key
            elif "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]
