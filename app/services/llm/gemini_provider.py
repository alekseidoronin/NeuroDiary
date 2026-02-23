"""
Google Gemini LLM provider — uses google.genai SDK.
"""

from __future__ import annotations

import logging

from google import genai
from google.genai import types

from app.config import settings
from app.dto.llm import LLMRequestDTO, LLMResultDTO
from app.services.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: str = "", model: str = ""):
        self._api_key = api_key or settings.GEMINI_API_KEY
        self._model = model or settings.GEMINI_MODEL
        # genai.Client has a known behavior where it might ignore passed api_key if not configured exactly right or if environment variables conflict.
        # However, the SDK explicitly supports `api_key`. Let's ensure it's passed as a kwarg clearly.
        self._client = genai.Client(api_key=self._api_key)

    async def generate(self, request: LLMRequestDTO) -> LLMResultDTO:
        logger.info("Gemini: generating for request %s (model=%s)", request.request_id, self._model)

        import os
        
        # google-genai 1.5.0 has a bug/behavior where it dynamically checks os.environ["GEMINI_API_KEY"] 
        # during the API call if it wasn't satisfied by the Client init.
        # We temporarily override the env var strictly for this call.
        original_key = os.environ.get("GEMINI_API_KEY")
        
        # We only override if we really need to and have a valid api_key
        if self._api_key:
            os.environ["GEMINI_API_KEY"] = self._api_key

        try:
            try:
                response = await self._client.aio.models.generate_content(
                    model=self._model,
                    contents=request.user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=request.system_prompt,
                        temperature=request.temperature,
                        max_output_tokens=request.max_tokens,
                    ),
                )
            finally:
                if original_key is not None:
                    os.environ["GEMINI_API_KEY"] = original_key
                elif "GEMINI_API_KEY" in os.environ:
                    del os.environ["GEMINI_API_KEY"]

            text = response.text or ""
            usage = response.usage_metadata
            tokens_in = usage.prompt_token_count if usage else 0
            tokens_out = usage.candidates_token_count if usage else 0

            logger.info("Gemini: response %d tokens_in, %d tokens_out", tokens_in, tokens_out)

            return LLMResultDTO(
                request_id=request.request_id,
                provider="gemini",
                model=self._model,
                final_text=text.strip(),
                status="ok",
                tokens_in=tokens_in,
                tokens_out=tokens_out,
            )

        except Exception as e:
            logger.exception("Gemini generation failed")
            return LLMResultDTO(
                request_id=request.request_id,
                provider="gemini",
                model=self._model,
                status="error",
                error_code="gemini_error",
                error_message=str(e),
            )
