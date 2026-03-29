"""
Google Gemini LLM provider — uses google.genai SDK.
Continues generation when output hits max_output_tokens (MAX_TOKENS).
"""

from __future__ import annotations

import logging

from google import genai
from google.genai import types

from app.config import settings
from app.dto.llm import LLMRequestDTO, LLMResultDTO
from app.services.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)

_GEMINI_MAX_CONTINUATION_ROUNDS = 12

_CONTINUE_PROMPT = (
    "Ответ оборвался по лимиту длины. Продолжи HTML-дневник ровно с места обрыва. "
    "Не повторяй уже выведенный текст — допиши только недостающий хвост, "
    "чтобы были закрыты все секции и пункты списков."
)


class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: str = "", model: str = ""):
        self._api_key = api_key or settings.GEMINI_API_KEY
        self._model = model or settings.GEMINI_MODEL
        self._client = genai.Client(api_key=self._api_key)

    async def generate(self, request: LLMRequestDTO) -> LLMResultDTO:
        logger.info("Gemini: generating for request %s (model=%s)", request.request_id, self._model)

        import os

        original_key = os.environ.get("GEMINI_API_KEY")
        if self._api_key:
            os.environ["GEMINI_API_KEY"] = self._api_key

        try:
            return await self._generate_with_continuation(request)
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
        finally:
            if original_key is not None:
                os.environ["GEMINI_API_KEY"] = original_key
            elif "GEMINI_API_KEY" in os.environ:
                del os.environ["GEMINI_API_KEY"]

    async def _generate_with_continuation(self, request: LLMRequestDTO) -> LLMResultDTO:
        contents: list[types.Content] = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=request.user_prompt)],
            )
        ]
        accumulated = ""
        total_completion = 0
        last_prompt_tokens = 0

        for round_idx in range(_GEMINI_MAX_CONTINUATION_ROUNDS):
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=request.system_prompt,
                    temperature=request.temperature,
                    max_output_tokens=request.max_tokens,
                ),
            )

            usage = response.usage_metadata
            if usage:
                last_prompt_tokens = usage.prompt_token_count or last_prompt_tokens
                total_completion += usage.candidates_token_count or 0

            if not response.candidates:
                logger.warning("Gemini: empty candidates (round %s)", round_idx)
                break

            try:
                chunk = response.text or ""
            except Exception as e:
                logger.warning("Gemini: could not read response.text: %s", e)
                break

            if round_idx > 0 and not chunk.strip():
                break
            accumulated += chunk

            cand = response.candidates[0]
            fr = getattr(cand, "finish_reason", None)
            if fr not in (types.FinishReason.MAX_TOKENS, "MAX_TOKENS"):
                if round_idx > 0:
                    logger.info("Gemini: continuation done after %s round(s)", round_idx + 1)
                break

            logger.warning(
                "Gemini: hit MAX_TOKENS (round %s/%s), continuing",
                round_idx + 1,
                _GEMINI_MAX_CONTINUATION_ROUNDS,
            )
            contents.append(
                types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=chunk)],
                )
            )
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=_CONTINUE_PROMPT)],
                )
            )

        final = accumulated.strip()
        if not final:
            return LLMResultDTO(
                request_id=request.request_id,
                provider="gemini",
                model=self._model,
                status="error",
                error_code="gemini_empty",
                error_message="Empty model response",
            )

        logger.info(
            "Gemini: done %d prompt_tokens (last round), %d completion_tokens (sum rounds)",
            last_prompt_tokens,
            total_completion,
        )

        return LLMResultDTO(
            request_id=request.request_id,
            provider="gemini",
            model=self._model,
            final_text=final,
            status="ok",
            tokens_in=last_prompt_tokens,
            tokens_out=total_completion,
        )
