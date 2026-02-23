"""
Usage & billing service — checks limits before processing.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import UsageDaily, Subscription, Plan, User

logger = logging.getLogger(__name__)


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

    # Define limits
    # Priority 1: Admin Overrides
    if user.limit_overrides and isinstance(user.limit_overrides, dict):
        max_entries = int(user.limit_overrides.get("entries_count", limits.get("entries_per_day", 5)))
        max_stt = int(user.limit_overrides.get("stt_seconds", limits.get("stt_seconds_per_day", 600)))
    else:
        # Priority 2: Plan limits
        max_entries = limits.get("entries_per_day", 5)
        max_stt = limits.get("stt_seconds_per_day", 600)

    # Check limits
    if total_entries >= max_entries:
        return {
            "allowed": False,
            "reason": f"Лимит пробного периода исчерпан ({total_entries}/{max_entries} записей).",
            "plan": plan_name,
        }

    if total_stt >= max_stt:
        return {
            "allowed": False,
            "reason": f"Лимит пробного периода исчерпан ({int(total_stt/60)}/{int(max_stt/60)} мин).",
            "plan": plan_name,
        }

    return {"allowed": True, "reason": None, "plan": plan_name}


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
