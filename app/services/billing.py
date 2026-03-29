"""
Usage & billing service — checks limits before processing.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional, Any
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import UsageDaily, Subscription, Plan, User

logger = logging.getLogger(__name__)


def _to_int(value: Any, default: int) -> int:
    """Safe int conversion with fallback."""
    if value is None:
        return int(default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _normalize_user_limit_overrides(raw: Any) -> dict[str, int]:
    """
    Normalize user limit overrides with backward compatibility.
    Supported keys:
      - entries_per_day (preferred)
      - stt_seconds_per_day (preferred)
      - entries_count (legacy)
      - stt_seconds (legacy)
    """
    if not isinstance(raw, dict):
        return {}

    out: dict[str, int] = {}
    entries_val = raw.get("entries_per_day", raw.get("entries_count"))
    stt_val = raw.get("stt_seconds_per_day", raw.get("stt_seconds"))

    if entries_val is not None:
        out["entries_per_day"] = _to_int(entries_val, 0)
    if stt_val is not None:
        out["stt_seconds_per_day"] = _to_int(stt_val, 0)
    return out


def resolve_effective_limits(user: User, plan_limits: dict[str, Any]) -> dict[str, Any]:
    """
    Resolve effective limits and source with a single priority chain:
      1) user.limit_overrides
      2) plan/global limits passed in plan_limits
    Returns diagnostics for UI/logging.
    """
    base_entries = _to_int(plan_limits.get("entries_per_day", 5), 5)
    base_stt = _to_int(plan_limits.get("stt_seconds_per_day", 600), 600)

    normalized = _normalize_user_limit_overrides(user.limit_overrides)
    if normalized:
        max_entries = _to_int(normalized.get("entries_per_day"), base_entries)
        max_stt = _to_int(normalized.get("stt_seconds_per_day"), base_stt)
        source = "user_override"
    else:
        max_entries = base_entries
        max_stt = base_stt
        source = "plan_or_default"

    return {
        "entries_per_day": max_entries,
        "stt_seconds_per_day": max_stt,
        "entries_unlimited": max_entries < 0,
        "stt_unlimited": max_stt < 0,
        "source": source,
    }


async def check_limits(db: AsyncSession, user: User) -> dict:
    """
    Check if the user is within their daily limits.
    Returns {"allowed": True/False, "reason": str | None, "plan": str}
    """
    if user.role == "admin":
        return {"allowed": True, "reason": None, "plan": "admin_unlimited"}

    user_id = user.id
    today = date.today()

    # Get active subscription
    sub_q = (
        select(Subscription, Plan)
        .join(Plan, Subscription.plan_id == Plan.id)
        .where(Subscription.user_id == user_id)
        .where(Subscription.status.in_(["trial", "active"]))
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    result = await db.execute(sub_q)
    row = result.first()

    if row:
        sub, plan = row
        limits = plan.limits_json or {}
        plan_name = plan.code
    else:
        # Default trial limits from config (or dynamic overrides)
        from app.services.settings import DynamicSettings
        ds = DynamicSettings(db)
        
        entries_limit = await ds.get("trial_entries_per_day", settings.TRIAL_ENTRIES_PER_DAY)
        stt_limit = await ds.get("trial_stt_seconds_per_day", settings.TRIAL_STT_SECONDS_PER_DAY)
        
        limits = {
            "entries_per_day": int(entries_limit),
            "stt_seconds_per_day": int(stt_limit),
        }
        plan_name = "trial_default"

    # Get TODAY's usage only
    usage_q = select(
        func.sum(UsageDaily.entries_count),
        func.sum(UsageDaily.stt_seconds)
    ).where(UsageDaily.user_id == user_id, UsageDaily.date == today)
    
    row = (await db.execute(usage_q)).first()
    total_entries = row[0] or 0
    total_stt = row[1] or 0

    effective = resolve_effective_limits(user, limits)
    max_entries = effective["entries_per_day"]
    max_stt = effective["stt_seconds_per_day"]
    entries_unlimited = effective["entries_unlimited"]
    stt_unlimited = effective["stt_unlimited"]

    # Check limits
    if (not entries_unlimited) and total_entries >= max_entries:
        return {
            "allowed": False,
            "reason": f"Лимит пробного периода исчерпан ({total_entries}/{max_entries} записей).",
            "plan": plan_name,
            "source": effective["source"],
            "effective_limits": effective,
        }

    if (not stt_unlimited) and total_stt >= max_stt:
        return {
            "allowed": False,
            "reason": f"Лимит пробного периода исчерпан ({int(total_stt/60)}/{int(max_stt/60)} мин).",
            "plan": plan_name,
            "source": effective["source"],
            "effective_limits": effective,
        }

    return {
        "allowed": True,
        "reason": None,
        "plan": plan_name,
        "source": effective["source"],
        "effective_limits": effective,
    }


async def increment_usage(
    db: AsyncSession,
    user_id: UUID,
    entries: int = 0,
    stt_seconds: int = 0,
    tokens_in: int = 0,
    tokens_out: int = 0,
) -> None:
    """Increment daily usage counters (upsert)."""
    today = date.today()

    usage_q = select(UsageDaily).where(
        UsageDaily.user_id == user_id,
        UsageDaily.date == today,
    )
    result = await db.execute(usage_q)
    usage = result.scalar_one_or_none()

    if usage is None:
        usage = UsageDaily(
            user_id=user_id,
            date=today,
            entries_count=entries,
            stt_seconds=stt_seconds,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
        )
        db.add(usage)
    else:
        usage.entries_count += entries
        usage.stt_seconds += stt_seconds
        usage.tokens_in += tokens_in
        usage.tokens_out += tokens_out

    await db.flush()
