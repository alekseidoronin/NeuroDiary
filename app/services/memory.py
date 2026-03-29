"""
Long-term user memory helpers.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import JournalEntry, UserFact

_CITY_PATTERNS = [
    re.compile(r"\bжив[ау]\s+в\s+([А-ЯA-Z][а-яa-zA-Z-]+)", re.IGNORECASE),
    re.compile(r"\bя\s+из\s+([А-ЯA-Z][а-яa-zA-Z-]+)", re.IGNORECASE),
]
_ALINA_PATTERN = re.compile(r"\bАлин[аыeуой]?\b", re.IGNORECASE)


async def get_user_facts(
    db: AsyncSession,
    user_id,
    *,
    limit: int = 15,
) -> list[UserFact]:
    result = await db.execute(
        select(UserFact)
        .where(UserFact.user_id == user_id)
        .order_by(desc(UserFact.last_seen_at))
        .limit(limit)
    )
    return list(result.scalars().all())


def format_facts_for_prompt(facts: Iterable[UserFact], max_chars: int = 1200) -> str:
    lines: list[str] = []
    used = 0
    for fact in facts:
        line = f"- {fact.fact_key}: {fact.fact_value}"
        if used + len(line) + 1 > max_chars:
            break
        lines.append(line)
        used += len(line) + 1
    return "\n".join(lines)


def extract_facts_from_text(text: str) -> list[tuple[str, str, float]]:
    if not text:
        return []

    facts: list[tuple[str, str, float]] = []
    lowered = text.lower()

    for pattern in _CITY_PATTERNS:
        match = pattern.search(text)
        if match:
            city = match.group(1).strip().title()
            facts.append(("home_city", city, 0.85))
            break

    if _ALINA_PATTERN.search(text):
        facts.append(("person_alina", "Алина — важный человек в окружении пользователя", 0.65))

    if "цель" in lowered or "план" in lowered:
        facts.append(("main_goal_now", "Пользователь регулярно формулирует цели и планы", 0.55))

    return facts


async def upsert_user_facts(
    db: AsyncSession,
    user_id,
    facts: list[tuple[str, str, float]],
    *,
    source_entry_id=None,
) -> None:
    if not facts:
        return

    now = datetime.now(timezone.utc)
    for key, value, confidence in facts:
        result = await db.execute(
            select(UserFact)
            .where(UserFact.user_id == user_id)
            .where(UserFact.fact_key == key)
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.fact_value = value
            existing.confidence = confidence
            existing.source_entry_id = source_entry_id
            existing.last_seen_at = now
        else:
            db.add(
                UserFact(
                    user_id=user_id,
                    fact_key=key,
                    fact_value=value,
                    confidence=confidence,
                    source_entry_id=source_entry_id,
                    last_seen_at=now,
                )
            )


async def get_last_entry_for_user(db: AsyncSession, user_id) -> JournalEntry | None:
    result = await db.execute(
        select(JournalEntry)
        .where(JournalEntry.user_id == user_id)
        .where(JournalEntry.status == "ok")
        .where(JournalEntry.is_admin_entry == False)
        .order_by(desc(JournalEntry.created_at))
        .limit(1)
    )
    return result.scalar_one_or_none()
