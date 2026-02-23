"""
Main processing pipeline — end-to-end orchestration.

Telegram message → normalise → (STT) → LLM → validate → reply.
"""

from __future__ import annotations

import logging
import uuid
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dto.telegram import InputNormalizedDTO
from app.dto.stt import STTRequestDTO
from app.dto.llm import LLMRequestDTO
from app.db.models import JournalEntry, ProviderJob, User
from app.services.stt.assemblyai_provider import AssemblyAIProvider
from app.services.llm.gemini_provider import GeminiProvider
from app.services.llm.openai_provider import OpenAIProvider
from app.services.prompts import SYSTEM_PROMPT, USER_TEMPLATE, REPAIR_PROMPT
from app.services.validator import validate_format, is_clarification_question
from app.services.events import log_event
from app.services.billing import check_limits, increment_usage

logger = logging.getLogger(__name__)

# ── Provider factories ──────────────────────────────────────

_stt_providers = {
    "assemblyai": AssemblyAIProvider,
}

_llm_providers = {
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
}


def get_stt_provider(name: str, api_key: str = ""):
    cls = _stt_providers.get(name)
    if not cls:
        raise ValueError(f"Unknown STT provider: {name}")
    return cls(api_key=api_key)


def get_llm_provider(name: str, api_key: str = "", model: str = ""):
    cls = _llm_providers.get(name)
    if not cls:
        raise ValueError(f"Unknown LLM provider: {name}")
    return cls(api_key=api_key, model=model)


# ── Telegram file download ──────────────────────────────────

async def download_telegram_file(file_id: str) -> bytes:
    """Download file from Telegram by file_id."""
    token = settings.TELEGRAM_BOT_TOKEN
    async with httpx.AsyncClient(timeout=60) as client:
        # 1. Get file path
        resp = await client.get(
            f"https://api.telegram.org/bot{token}/getFile",
            params={"file_id": file_id},
        )
        resp.raise_for_status()
        file_path = resp.json()["result"]["file_path"]

        # 2. Download
        resp = await client.get(
            f"https://api.telegram.org/file/bot{token}/{file_path}"
        )
        resp.raise_for_status()
        return resp.content


# ── Local datetime helper ───────────────────────────────────

def _local_now(tz_name: str = "Asia/Dubai") -> str:
    """Return local datetime string for the given timezone offset."""
    # Simple offset map for common timezones
    offsets = {
        "Asia/Dubai": 4,
        "Europe/Moscow": 3,
        "UTC": 0,
    }
    offset_hours = offsets.get(tz_name, 4)
    tz = timezone(timedelta(hours=offset_hours))
    return datetime.now(tz).strftime("%Y.%m.%d %H:%M")


# ── Main pipeline ───────────────────────────────────────────

async def process_message(
    db: AsyncSession,
    inp: InputNormalizedDTO,
    user: User,
) -> dict:
    """
    Full processing pipeline.
    Returns: {"type": "entry"|"clarification"|"error"|"paywall", "text": str}
    """
    from app.services.settings import DynamicSettings
    ds = DynamicSettings(db)
    request_id = inp.request_id

    # 1. Check limits
    limits = await check_limits(db, user)
    if not limits["allowed"]:
        await log_event(db, "paywall_shown", user.id, {"reason": limits["reason"]})
        await db.commit()
        return {"type": "paywall", "text": f"⚠️ {limits['reason']}"}

    # 2. Get text (STT if voice/audio)
    raw_text = inp.raw_text
    stt_duration = 0

    if inp.input_type in ("voice", "audio"):
        raw_text, stt_duration = await _run_stt(db, ds, inp, user)
        if raw_text is None:
            await db.commit()
            return {
                "type": "error",
                "text": "❌ Не удалось расшифровать голосовое сообщение. Попробуй ещё раз или отправь текстом.",
            }

    if not raw_text or not raw_text.strip():
        return {"type": "error", "text": "⚠️ Пустое сообщение. Отправь текст или голос!"}

    # 3. Call LLM
    llm_text, t_in, t_out = await _run_llm(db, ds, request_id, user, raw_text, inp)
    
    if llm_text is None:
        await db.commit()
        return {
            "type": "error",
            "text": "❌ Ошибка генерации записи. Попробуй ещё раз.",
        }

    # 4. Check if it's a clarification question
    if is_clarification_question(llm_text):
        await log_event(db, "clarification_asked", user.id)
        await db.commit()
        return {"type": "clarification", "text": llm_text}

    # 5. Validate format
    validation = validate_format(llm_text, request_id)

    if not validation.is_valid:
        # One repair attempt
        logger.info("Format invalid for %s — attempting repair", request_id)
        repaired_text, r_t_in, r_t_out = await _run_repair(db, ds, request_id, user, llm_text)
        
        # Add repair tokens to total
        t_in = (t_in or 0) + (r_t_in or 0)
        t_out = (t_out or 0) + (r_t_out or 0)

        if repaired_text:
            llm_text = repaired_text
            validation.repair_attempted = True
            # Re-validate
            validation = validate_format(llm_text, request_id)

    # 6. Final cleanup
    from app.services.validator import _CODE_BLOCK_RE
    code_blocks = _CODE_BLOCK_RE.findall(llm_text)
    if code_blocks:
        llm_text = code_blocks[0].strip()
    else:
        llm_text = re.sub(r"```(?:\w+)?\s*", "", llm_text).replace("```", "").strip()

    # 6a. Extract mood
    mood = None
    mood_match = re.search(r"\[\[MOOD:\s*(\w+)\]\]", llm_text)
    if mood_match:
        mood = mood_match.group(1).lower()
        llm_text = re.sub(r"\s*\[\[MOOD:\s*\w+\]\]", "", llm_text).strip()

    # 7. Save journal entry
    entry = JournalEntry(
        user_id=user.id,
        source_message_id=inp.message_id,
        input_type=inp.input_type,
        raw_input_text=inp.raw_text,
        transcript_text=raw_text if inp.input_type != "text" else None,
        final_diary_text=llm_text,
        status="ok",
        is_admin_entry=user.role == "admin",
        # Usage Stats
        usage_tokens_in=t_in,
        usage_tokens_out=t_out,
        usage_audio_duration=int(stt_duration or 0),
        mood=mood,
    )
    db.add(entry)

    # 7. Update usage
    await increment_usage(
        db, user.id,
        entries=1,
        stt_seconds=int(stt_duration or 0),
    )

    await log_event(db, "diary_sent", user.id, {
        "entry_id": str(entry.id),
        "input_type": inp.input_type,
        "repair_attempted": validation.repair_attempted,
    })

    await db.commit()

    return {"type": "entry", "text": llm_text, "entry_id": entry.id}


# ── Sub-steps ───────────────────────────────────────────────

async def _run_stt(db: AsyncSession, ds: Any, inp: InputNormalizedDTO, user: User):
    """Download audio + transcribe. Returns (text, duration) or (None, 0)."""
    request_id = inp.request_id

    try:
        audio_bytes = await download_telegram_file(inp.telegram_file_id)
    except Exception as e:
        logger.exception("Failed to download Telegram file")
        await log_event(db, "stt_download_error", user.id, {"error": str(e)})
        return None, 0

    provider_name = await ds.get_stt_provider()
    api_key = await ds.get_stt_api_key(provider_name)
    stt_provider = get_stt_provider(provider_name, api_key=api_key)

    stt_req = STTRequestDTO(
        request_id=request_id,
        audio_bytes=audio_bytes,
        language="ru",
    )

    # Record provider job
    stt_job_id = uuid.uuid4()
    job = ProviderJob(
        request_id=stt_job_id,
        user_id=user.id,
        kind="stt",
        provider=provider_name,
    )
    db.add(job)
    await db.flush()

    stt_result = await stt_provider.transcribe(stt_req)

    job.status = stt_result.status
    job.provider_job_id = stt_result.provider_job_id
    job.duration_seconds = stt_result.duration_seconds
    if stt_result.status == "error":
        job.error_message = stt_result.error_message

    await log_event(db, "stt_done", user.id, {
        "status": stt_result.status,
        "duration": stt_result.duration_seconds,
        "provider": stt_result.provider,
    })

    if stt_result.status != "ok":
        return None, 0

    return stt_result.transcript_text, stt_result.duration_seconds or 0


async def _run_llm(db, ds, request_id, user, raw_text, inp):
    """Call LLM with diary prompt. Returns final text or None."""
    provider_name = await ds.get_llm_provider()
    model_name = await ds.get_llm_model(provider_name)
    api_key = await ds.get_llm_api_key(provider_name)

    llm_provider = get_llm_provider(provider_name, api_key=api_key, model=model_name)

    system_prompt = await ds.get_system_prompt(user)
    user_template = await ds.get_user_template(user)

    user_prompt = user_template.format(
        local_datetime=_local_now(inp.timezone),
        timezone=inp.timezone,
        location="Dubai",
        input_type=inp.input_type,
        raw_text=raw_text,
    )

    temp = await ds.get("llm_temperature", settings.LLM_TEMPERATURE)
    max_tokens = await ds.get("llm_max_tokens", settings.LLM_MAX_TOKENS)

    llm_req = LLMRequestDTO(
        request_id=request_id,
        provider=provider_name,
        model=model_name,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=float(temp),
        max_tokens=int(max_tokens),
    )

    # Record provider job
    llm_job_id = uuid.uuid4()
    job = ProviderJob(
        request_id=llm_job_id,
        user_id=user.id,
        kind="llm",
        provider=provider_name,
        model=llm_req.model,
    )
    db.add(job)
    await db.flush()

    llm_result = await llm_provider.generate(llm_req)

    job.status = llm_result.status
    job.tokens_in = llm_result.tokens_in
    job.tokens_out = llm_result.tokens_out
    if llm_result.status == "error":
        job.error_message = llm_result.error_message

    await log_event(db, "llm_done", user.id, {
        "status": llm_result.status,
        "tokens_in": llm_result.tokens_in,
        "tokens_out": llm_result.tokens_out,
        "provider": llm_result.provider,
    })

    await increment_usage(
        db, user.id,
        tokens_in=llm_result.tokens_in,
        tokens_out=llm_result.tokens_out,
    )

    if llm_result.status != "ok":
        return None, 0, 0

    return llm_result.final_text, llm_result.tokens_in, llm_result.tokens_out


async def _run_repair(db, ds, request_id, user, broken_text):
    """One repair pass via the same LLM."""
    repair_id = uuid.uuid4()

    provider_name = await ds.get_llm_provider()
    model_name = await ds.get_llm_model(provider_name)
    api_key = await ds.get_llm_api_key(provider_name)

    llm_provider = get_llm_provider(provider_name, api_key=api_key, model=model_name)
    repair_prompt = await ds.get_repair_prompt()

    llm_req = LLMRequestDTO(
        request_id=repair_id,
        provider=provider_name,
        model=model_name,
        system_prompt=repair_prompt,
        user_prompt=broken_text,
        temperature=0.2,
        max_tokens=settings.LLM_MAX_TOKENS,
    )

    job = ProviderJob(
        request_id=repair_id,
        user_id=user.id,
        kind="repair",
        provider=provider_name,
        model=model_name,
    )
    db.add(job)
    await db.flush()

    result = await llm_provider.generate(llm_req)

    job.status = result.status
    job.tokens_in = result.tokens_in
    job.tokens_out = result.tokens_out
    if result.status == "error":
        job.error_message = result.error_message

    await log_event(db, "repair_done", user.id, {
        "status": result.status,
        "tokens_in": result.tokens_in,
        "tokens_out": result.tokens_out,
    })

    if result.status != "ok":
        logger.warning("Repair failed for %s", request_id)
        return None, 0, 0

    return result.final_text, result.tokens_in, result.tokens_out
