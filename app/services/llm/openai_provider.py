"""
OpenAI ChatGPT LLM provider.
Continues when finish_reason is "length" (max completion tokens).
"""

from __future__ import annotations

import logging

from openai import AsyncOpenAI

from app.config import settings
from app.dto.llm import LLMRequestDTO, LLMResultDTO
from app.services.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)

_OPENAI_MAX_CONTINUATION_ROUNDS = 12

_CONTINUE_PROMPT = (
    "Ответ оборвался по лимиту длины. Продолжи HTML-дневник ровно с места обрыва. "
    "Не повторяй уже выведенный текст — допиши только недостающий хвост, "
    "чтобы были закрыты все секции и пункты списков."
)


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
            messages: list[dict] = [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ]
            accumulated = ""
            total_in = 0
            total_out = 0

            for round_idx in range(_OPENAI_MAX_CONTINUATION_ROUNDS):
                response = await self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                )

                choice = response.choices[0]
                chunk = choice.message.content or ""
                fr = choice.finish_reason

                usage = response.usage
                if usage:
                    total_in = usage.prompt_tokens or total_in
                    total_out += usage.completion_tokens or 0

                if round_idx > 0 and not chunk.strip():
                    break
                accumulated += chunk

                if fr != "length":
                    if round_idx > 0:
                        logger.info("OpenAI: continuation done after %s round(s)", round_idx + 1)
                    break

                logger.warning(
                    "OpenAI: hit length limit (round %s/%s), continuing",
                    round_idx + 1,
                    _OPENAI_MAX_CONTINUATION_ROUNDS,
                )
                messages.append({"role": "assistant", "content": chunk})
                messages.append({"role": "user", "content": _CONTINUE_PROMPT})

            final = accumulated.strip()
            if not final:
                return LLMResultDTO(
                    request_id=request.request_id,
                    provider="openai",
                    model=self._model,
                    status="error",
                    error_code="openai_empty",
                    error_message="Empty model response",
                )

            logger.info("OpenAI: response %d tokens_in, %d tokens_out", total_in, total_out)

            return LLMResultDTO(
                request_id=request.request_id,
                provider="openai",
                model=self._model,
                final_text=final,
                status="ok",
                tokens_in=total_in,
                tokens_out=total_out,
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
