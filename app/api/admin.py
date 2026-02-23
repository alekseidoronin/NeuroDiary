"""
Admin API endpoints — used by the Telegram Mini App.
All endpoints require admin role (validated via Telegram init data).
"""

from __future__ import annotations

import logging
import asyncio
from datetime import date, datetime, timedelta
from typing import Optional
from uuid import UUID

from app.services.events import log_event

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import func, select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.types import MenuButtonWebApp, WebAppInfo

from app.api.auth import get_admin_user
from app.db.engine import get_db
from app.db.models import (
    User, JournalEntry, Event, ProviderJob,
    Plan, Subscription, Payment, UsageDaily, BotSettings,
    AffiliateRecord,
)
from app.config import settings

logger = logging.getLogger(__name__)

admin_router = APIRouter(prefix="/admin", tags=["admin"])


# ── Helpers ──────────────────────────────────────────────────

async def _sync_user_menu_button(tg_user_id: int, role: str):
    """
    Update Telegram menu button based on user role.
    If 'admin', show 'Admin' button.
    If 'user', remove menu button (show default).
    """
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    try:
        url = settings.MINI_APP_URL
        if not url:
            logger.warning("MINI_APP_URL not set in settings. Skipping menu button sync.")
            return

        if role == "admin":
            await bot.set_chat_menu_button(
                chat_id=tg_user_id,
                menu_button=MenuButtonWebApp(
                    text="Админка", 
                    web_app=WebAppInfo(url=url)
                )
            )
            logger.info(f"Set admin menu button for user {tg_user_id}")
        else:
            # Swith to default (show commands list, NOT the BotFather fallback)
            await bot.set_chat_menu_button(
                chat_id=tg_user_id,
                menu_button=MenuButtonCommands()
            )
            logger.info(f"Reset menu button for user {tg_user_id}")
    except Exception as e:
        logger.error(f"Failed to sync menu button for {tg_user_id}: {e}")
    finally:
        await bot.session.close()


async def _upsert_setting(
    db: AsyncSession,
    key: str,
    value: str,
    admin_id: UUID,
    is_secret: bool = False,
):
    """Insert or update a bot setting."""
    result = await db.execute(select(BotSettings).where(BotSettings.key == key))
    setting = result.scalar_one_or_none()

    if setting is None:
        setting = BotSettings(key=key, is_secret=is_secret)
        db.add(setting)

    if is_secret:
        from app.services.crypto import encrypt_value
        setting.encrypted_value = encrypt_value(value)
        setting.value = None
    else:
        setting.value = value

    setting.version = (setting.version or 0) + 1
    setting.updated_by = admin_id
    await db.flush()


# ── Dashboard ────────────────────────────────────────────────

@admin_router.get("/me")
async def admin_me(admin: User = Depends(get_admin_user)):
    return {
        "id": str(admin.id),
        "tg_user_id": admin.tg_user_id,
        "username": admin.username,
        "role": admin.role,
    }


@admin_router.get("/dashboard")
async def dashboard(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    if not from_date:
        from_date = date.today() - timedelta(days=7)
    if not to_date:
        to_date = date.today()

    # DAU
    dau_q = (
        select(func.count(func.distinct(Event.user_id)))
        .where(Event.event_name == "message_received")
        .where(func.date(Event.created_at) == date.today())
    )
    dau_result = await db.execute(dau_q)
    dau = dau_result.scalar() or 0

    # WAU
    week_ago = date.today() - timedelta(days=7)
    wau_q = (
        select(func.count(func.distinct(Event.user_id)))
        .where(Event.event_name == "message_received")
        .where(func.date(Event.created_at) >= week_ago)
    )
    wau_result = await db.execute(wau_q)
    wau = wau_result.scalar() or 0

    # Total users
    total_users_q = select(func.count(User.id))
    total_users_result = await db.execute(total_users_q)
    total_users = total_users_result.scalar() or 0

    # Entries today
    entries_today_q = (
        select(func.count(JournalEntry.id))
        .where(func.date(JournalEntry.created_at) == date.today())
    )
    entries_today_result = await db.execute(entries_today_q)
    entries_today = entries_today_result.scalar() or 0

    # Voice vs Text ratio (last 7 days)
    voice_q = (
        select(func.count(JournalEntry.id))
        .where(JournalEntry.input_type.in_(["voice", "audio"]))
        .where(func.date(JournalEntry.created_at) >= week_ago)
    )
    text_q = (
        select(func.count(JournalEntry.id))
        .where(JournalEntry.input_type == "text")
        .where(func.date(JournalEntry.created_at) >= week_ago)
    )
    voice_count = (await db.execute(voice_q)).scalar() or 0
    text_count = (await db.execute(text_q)).scalar() or 0

    # Errors (last 7 days)
    errors_q = (
        select(func.count(ProviderJob.id))
        .where(ProviderJob.status == "error")
        .where(func.date(ProviderJob.started_at) >= week_ago)
    )
    errors = (await db.execute(errors_q)).scalar() or 0

    # 5. Activity Heatmap (Last 365 Days)
    year_ago = datetime.now() - timedelta(days=365)
    
    q_heatmap = select(
        func.date(JournalEntry.created_at).label('day'), 
        func.count(JournalEntry.id)
    ).where(
        JournalEntry.created_at >= year_ago
    ).group_by(
        func.date(JournalEntry.created_at)
    )
    
    heatmap_res = await db.execute(q_heatmap)
    heatmap_map = {row[0].strftime("%Y-%m-%d"): row[1] for row in heatmap_res.all()}
    
    heatmap_data = []
    for date_str, count in heatmap_map.items():
        heatmap_data.append({"date": date_str, "count": count})

    return {
        "dau": dau,
        "wau": wau,
        "total_users": total_users,
        "entries_today": entries_today,
        "voice_count_7d": voice_count,
        "text_count_7d": text_count,
        "errors_7d": errors,
        "heatmap": heatmap_data
    }


# ── Users ────────────────────────────────────────────────────

@admin_router.get("/users")
async def list_users(
    search: Optional[str] = Query(None),
    offset: int = Query(0),
    limit: int = Query(50),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    q = select(User).order_by(desc(User.last_seen_at))
    if search:
        q = q.where(
            User.username.ilike(f"%{search}%") |
            User.first_name.ilike(f"%{search}%")
        )
    q = q.offset(offset).limit(limit)

    result = await db.execute(q)
    users = result.scalars().all()

    return [
        {
            "id": str(u.id),
            "tg_user_id": u.tg_user_id,
            "username": u.username,
            "first_name": u.first_name,
            "role": u.role,
            "status": u.status,
            "locale": u.locale,
            "timezone": u.timezone,
            "first_seen_at": u.first_seen_at.isoformat() if u.first_seen_at else None,
            "last_seen_at": u.last_seen_at.isoformat() if u.last_seen_at else None,
        }
        for u in users
    ]


@admin_router.post("/users")
async def create_user(
    data: dict,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    tg_id = data.get("tg_user_id")
    if not tg_id:
        raise HTTPException(400, "tg_user_id is required")
    
    # Check if exists
    res = await db.execute(select(User).where(User.tg_user_id == tg_id))
    if res.scalar_one_or_none():
        raise HTTPException(400, "User already exists")

    user = User(
        tg_user_id=tg_id,
        username=data.get("username"),
        first_name=data.get("first_name"),
        role=data.get("role", "user"),
        status=data.get("status", "active"),
        locale=data.get("locale", "ru"),
        timezone=data.get("timezone", "Asia/Dubai"),
    )
    db.add(user)
    await db.commit()

    # Sync telegram menu button
    await _sync_user_menu_button(tg_id, user.role)

    return {"status": "ok", "user_id": str(user.id)}


@admin_router.get("/users/{user_id}")
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    # Last events
    events_q = (
        select(Event)
        .where(Event.user_id == user_id)
        .order_by(desc(Event.created_at))
        .limit(20)
    )
    events_result = await db.execute(events_q)
    events = events_result.scalars().all()

    # Usage TOTAL (renaming query but keeping response key for now)
    usage_q = select(
        func.sum(UsageDaily.entries_count),
        func.sum(UsageDaily.stt_seconds),
        func.sum(UsageDaily.tokens_in),
        func.sum(UsageDaily.tokens_out)
    ).where(UsageDaily.user_id == user_id)
    
    usage_row = (await db.execute(usage_q)).first()
    
    total_entries = usage_row[0] or 0
    total_stt = usage_row[1] or 0
    total_tokens_in = usage_row[2] or 0
    total_tokens_out = usage_row[3] or 0

    # Calculate Total Cost (Estimate)
    # 1. Get raw sums
    cost_q = select(
        func.sum(UsageDaily.tokens_in),
        func.sum(UsageDaily.tokens_out),
        func.sum(UsageDaily.stt_seconds)
    ).where(UsageDaily.user_id == user_id)
    
    cost_row = (await db.execute(cost_q)).first()
    t_in = cost_row[0] or 0
    t_out = cost_row[1] or 0
    stt_sec = cost_row[2] or 0
    
    # Precise pricing logic (USD)
    # AssemblyAI Best: $0.37 / hr
    # Gemini 1.5 Flash: In $0.075/1M, Out $0.30/1M
    PRICE_STT_SEC_USD = 0.37 / 3600
    PRICE_TOKEN_IN_USD = 0.075 / 1_000_000
    PRICE_TOKEN_OUT_USD = 0.30 / 1_000_000
    
    total_cost_usd = (stt_sec * PRICE_STT_SEC_USD) + \
                     (t_in * PRICE_TOKEN_IN_USD) + \
                     (t_out * PRICE_TOKEN_OUT_USD)
    
    total_cost_usd = round(float(total_cost_usd), 4)

    # Activity History (Last 30 Days)
    history_start = date.today() - timedelta(days=29)
    history_q = select(
        UsageDaily.date,
        UsageDaily.entries_count,
        UsageDaily.stt_seconds,
        UsageDaily.tokens_total
    ).where(
        UsageDaily.user_id == user_id,
        UsageDaily.date >= history_start
    ).order_by(UsageDaily.date)
    
    history_rows = (await db.execute(history_q)).all()
    
    # Fill gaps
    history_map = {row.date: row for row in history_rows}
    history_data = []
    for i in range(30):
        d = history_start + timedelta(days=i)
        if d in history_map:
            row = history_map[d]
            history_data.append({
                "date": d.strftime("%Y-%m-%d"),
                "entries": row.entries_count,
                "stt_seconds": float(row.stt_seconds or 0),
                "tokens": row.tokens_total
            })
        else:
            history_data.append({
                "date": d.strftime("%Y-%m-%d"),
                "entries": 0,
                "stt_seconds": 0,
                "tokens": 0
            })

    return {
        "user": {
            "id": str(user.id),
            "tg_user_id": user.tg_user_id,
            "username": user.username,
            "first_name": user.first_name,
            "role": user.role,
            "status": user.status,
            "locale": user.locale,
            "timezone": user.timezone,
            "last_seen_at": user.last_seen_at.isoformat() if user.last_seen_at else None,
            "first_seen_at": user.first_seen_at.isoformat() if user.first_seen_at else None,
            "balance": float(user.balance or 0),
            "limit_overrides": user.limit_overrides,
            "total_cost_usd": total_cost_usd, 
        },
        "usage_today": {
            "entries": total_entries,
            "stt_seconds": total_stt,
            "tokens_in": total_tokens_in,
            "tokens_out": total_tokens_out,
        },
        "recent_events": [
            {
                "event_name": e.event_name,
                "payload": e.payload,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ],
    }


@admin_router.post("/users/{user_id}")
async def update_user(
    user_id: UUID,
    data: dict,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    # Update fields if present
    role_changed = False
    for field in ["status", "role", "username", "first_name", "locale", "timezone", "custom_system_prompt"]:
        if field in data:
            if field == "role" and data[field] != user.role:
                role_changed = True
            setattr(user, field, data[field])

    await db.commit()

    # Sync telegram menu button if role changed (or force sync just in case)
    if user.tg_user_id:
        await _sync_user_menu_button(user.tg_user_id, user.role)

    return {"status": "ok"}


@admin_router.post("/users/{user_id}/topup")
async def top_up_user(
    user_id: UUID,
    data: dict,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    amount = data.get("amount", 0)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    user.balance = (user.balance or 0) + amount
    
    # Log payment
    payment = Payment(
        user_id=user_id,
        provider="manual",
        amount=amount,
        status="succeeded",
        currency="USD"
    )
    db.add(payment)
    await db.commit()
    return {"status": "ok", "new_balance": float(user.balance)}


@admin_router.post("/users/{user_id}/limits")
async def update_user_limits(
    user_id: UUID,
    data: dict,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    from sqlalchemy.orm.attributes import flag_modified
    user.limit_overrides = data
    flag_modified(user, "limit_overrides")
    await db.commit()
    return {"status": "ok"}


# ── Entries ──────────────────────────────────────────────────

@admin_router.get("/entries")
async def list_entries(
    user_id: Optional[UUID] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    status: Optional[str] = Query(None),
    offset: int = Query(0),
    limit: int = Query(50),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    q = select(JournalEntry).order_by(desc(JournalEntry.created_at))
    if user_id:
        q = q.where(JournalEntry.user_id == user_id)
    if from_date:
        q = q.where(func.date(JournalEntry.created_at) >= from_date)
    if to_date:
        q = q.where(func.date(JournalEntry.created_at) <= to_date)
    if status:
        q = q.where(JournalEntry.status == status)
    q = q.offset(offset).limit(limit)

    result = await db.execute(q)
    entries = result.scalars().all()

    def get_usage_and_cost(e):
        tokens_in = e.usage_tokens_in or 0
        tokens_out = e.usage_tokens_out or 0
        duration = float(e.usage_audio_duration or 0)
        
        # Estimate if zero (legacy data)
        # 1 token ~= 4 chars (using 3.5 to be safe/closer to Russian avg)
        if tokens_in == 0 and e.raw_input_text:
             tokens_in = len(e.raw_input_text) // 3.5
        if tokens_out == 0 and e.final_diary_text:
             tokens_out = len(e.final_diary_text) // 3.5
             
        # STT duration estimate
        if duration == 0 and e.input_type in ['voice', 'audio'] and e.transcript_text:
            # Estimate: ~2 words per sec (120 wpm)
            words = len(e.transcript_text.split())
            duration = words / 2.0 
            
        # Precise pricing logic (USD)
        # AssemblyAI Best: $0.37 / hr
        # Gemini 1.5 Flash: In $0.075/1M, Out $0.30/1M
        PRICE_STT_SEC_USD = 0.37 / 3600
        PRICE_TOKEN_IN_USD = 0.075 / 1_000_000
        PRICE_TOKEN_OUT_USD = 0.30 / 1_000_000
        
        cost_usd = (duration * PRICE_STT_SEC_USD) + \
                   (tokens_in * PRICE_TOKEN_IN_USD) + \
                   (tokens_out * PRICE_TOKEN_OUT_USD)
        
        return {
            "cost_usd": round(float(cost_usd), 6),
            "tokens_in": int(tokens_in),
            "tokens_out": int(tokens_out),
            "audio_duration": int(duration),
        }

    out = []
    for e in entries:
        stats = get_usage_and_cost(e)
        out.append({
            "id": str(e.id),
            "user_id": str(e.user_id),
            "input_type": e.input_type,
            "status": e.status,
            "raw_input_text": (e.raw_input_text or "")[:200],
            "transcript_text": (e.transcript_text or "")[:200],
            "final_diary_text": e.final_diary_text,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "is_admin_entry": e.is_admin_entry if hasattr(e, 'is_admin_entry') else False,
            "cost_usd": stats["cost_usd"],
            "usage": {
                "tokens_in": stats["tokens_in"],
                "tokens_out": stats["tokens_out"],
                "audio_duration": stats["audio_duration"],
            }
        })
    return out


@admin_router.post("/entries")
async def create_entry(
    data: dict,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    user_id = data.get("user_id")
    if not user_id:
        raise HTTPException(400, "user_id is required")

    entry = JournalEntry(
        user_id=UUID(user_id) if isinstance(user_id, str) else user_id,
        input_type=data.get("input_type", "text"),
        raw_input_text="Admin added",
        final_diary_text=data.get("text"),
        status="ok",
        entry_date=date.today(),
        is_admin_entry=True,
    )
    db.add(entry)
    await db.commit()
    return {"status": "ok", "entry_id": str(entry.id)}


@admin_router.patch("/entries/{entry_id}")
@admin_router.post("/entries/{entry_id}")
async def update_entry(
    entry_id: UUID,
    data: dict,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    result = await db.execute(select(JournalEntry).where(JournalEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(404, "Entry not found")

    old_text = entry.final_diary_text
    if "text" in data:
        entry.final_diary_text = data["text"]
    if "status" in data:
        entry.status = data["status"]

    await db.commit()

    # If text changed and we have bot_message_id, try to edit in Telegram
    if "text" in data and data["text"] != old_text and entry.bot_message_id:
        from app.core.bot import bot
        from aiogram.enums import ParseMode
        result_user = await db.execute(select(User).where(User.id == entry.user_id))
        user = result_user.scalar_one_or_none()
        if user and user.tg_user_id:
            try:
                await bot.edit_message_text(
                    chat_id=user.tg_user_id,
                    message_id=entry.bot_message_id,
                    text=entry.final_diary_text,
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                logger.warning(f"Failed to edit TG message: {e}")

    return {"status": "ok"}


@admin_router.post("/broadcast")
async def broadcast_message(
    data: dict,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    text = data.get("text")
    if not text:
        raise HTTPException(400, "text is required")

    result = await db.execute(select(User).where(User.status == 'active'))
    users = result.scalars().all()

    from app.core.bot import bot
    count = 0
    for u in users:
        if u.tg_user_id:
            try:
                await bot.send_message(chat_id=u.tg_user_id, text=text)
                count += 1
                await asyncio.sleep(0.05) # Rate limiting
            except Exception as e:
                logger.warning(f"Failed to send broadcast to {u.tg_user_id}: {e}")

    await log_event(db, "broadcast_sent", admin.id, {"text": text, "count": count})
    await db.commit()
    
    return {"status": "ok", "sent_count": count}


@admin_router.post("/users/{user_id}/summarize-week")
async def summarize_week(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    from app.services.summarizer import generate_weekly_summary
    from app.core.bot import bot
    from aiogram.enums import ParseMode

    summary = await generate_weekly_summary(db, user)
    
    if user.tg_user_id:
        try:
            await bot.send_message(
                chat_id=user.tg_user_id,
                text=f"📊 <b>Твой итог недели готов!</b>\n\n{summary}",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.warning(f"Failed to send summary to {user.tg_user_id}: {e}")

    return {"status": "ok", "summary": summary}


@admin_router.post("/users/{user_id}/message")
async def send_user_message(
    user_id: UUID,
    data: dict,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    text = data.get("text")
    if not text:
        raise HTTPException(400, "text is required")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.tg_user_id:
        raise HTTPException(404, "User not found or has no TG ID")

    from app.core.bot import bot
    try:
        await bot.send_message(chat_id=user.tg_user_id, text=text)
    except Exception as e:
        raise HTTPException(500, f"Telegram error: {e}")

    return {"status": "ok"}


@admin_router.delete("/entries/{entry_id}")
async def delete_entry(
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    result = await db.execute(select(JournalEntry).where(JournalEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(404, "Entry not found")

    await db.delete(entry)
    await db.commit()
    return {"status": "ok"}


# ── Events ───────────────────────────────────────────────────

@admin_router.get("/events")
async def list_events(
    user_id: Optional[UUID] = Query(None),
    event_name: Optional[str] = Query(None),
    offset: int = Query(0),
    limit: int = Query(100),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    q = select(Event).order_by(desc(Event.created_at))
    if user_id:
        q = q.where(Event.user_id == user_id)
    if event_name:
        q = q.where(Event.event_name == event_name)
    q = q.offset(offset).limit(limit)

    result = await db.execute(q)
    events = result.scalars().all()

    return [
        {
            "id": str(e.id),
            "user_id": str(e.user_id) if e.user_id else None,
            "event_name": e.event_name,
            "payload": e.payload,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in events
    ]


# ── Affiliate Program ───────────────────────────────────────

@admin_router.get("/affiliate/stats")
async def affiliate_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    # Overall program stats
    partners_q = select(func.count(func.distinct(AffiliateRecord.user_id)))
    partners_result = await db.execute(partners_q)
    total_partners = partners_result.scalar() or 0

    total_referrals_q = select(func.count(User.id)).where(User.referrer_id != None)
    total_referrals = (await db.execute(total_referrals_q)).scalar() or 0

    total_paid_q = select(func.sum(AffiliateRecord.amount))
    total_paid = (await db.execute(total_paid_q)).scalar() or 0

    return {
        "total_partners": total_partners,
        "total_referrals": total_referrals,
        "total_paid": float(total_paid or 0),
        "min_withdrawal": 1000,
        "commission_rate": 0.15,
    }


# ── Settings (providers, keys, prompts) ──────────────────────

@admin_router.get("/settings")
async def get_settings(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    result = await db.execute(select(BotSettings))
    db_settings = {s.key: s for s in result.scalars().all()}

    from app.services.prompts import SYSTEM_PROMPT, USER_TEMPLATE, REPAIR_PROMPT
    from app.config import settings as cfg

    keys = [
        "stt_provider", "llm_provider", "llm_model",
        "system_prompt", "user_template", "repair_prompt",
        "assemblyai_api_key", "openai_api_key", "gemini_api_key",
        "trial_entries_per_day", "trial_stt_seconds_per_day",
        "llm_temperature", "llm_max_tokens",
        "affiliate_commission_rate", "affiliate_min_withdrawal",
        "yoomoney_shop_id", "yoomoney_secret",
        "robokassa_merchant_id", "robokassa_password_1", "robokassa_password_2",
        "cryptobot_token"
    ]

    out = {}
    for k in keys:
        s = db_settings.get(k)
        if s:
            out[k] = {
                "value": s.value if not s.is_secret else "********",
                "is_secret": s.is_secret,
                "version": s.version,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
        else:
            # Get default from code
            default_val = "********"
            if k == "stt_provider": default_val = cfg.STT_PROVIDER
            elif k == "llm_provider": default_val = cfg.LLM_PROVIDER
            elif k == "llm_model": default_val = cfg.GEMINI_MODEL if cfg.LLM_PROVIDER == "gemini" else cfg.OPENAI_MODEL
            elif k == "system_prompt": default_val = SYSTEM_PROMPT
            elif k == "user_template": default_val = USER_TEMPLATE
            elif k == "repair_prompt": default_val = REPAIR_PROMPT
            
            out[k] = {
                "value": default_val,
                "is_secret": k.endswith("_key"),
                "is_default": True,
            }

    return out


@admin_router.post("/settings/providers")
async def update_providers(
    data: dict,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Update STT/LLM provider selection and model."""
    allowed = [
        "stt_provider", "llm_provider", "llm_model",
        "trial_entries_per_day", "trial_stt_seconds_per_day",
        "llm_temperature", "llm_max_tokens"
    ]
    for key in allowed:
        if key in data:
            await _upsert_setting(db, key, str(data[key]), admin.id)
    await db.commit()
    return {"status": "ok"}


@admin_router.post("/settings/secrets")
async def update_secrets(
    data: dict,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Update API keys (stored encrypted)."""
    for key in ["assemblyai_api_key", "openai_api_key", "gemini_api_key"]:
        if key in data and data[key]:
            await _upsert_setting(db, key, data[key], admin.id, is_secret=True)
    await db.commit()
    return {"status": "ok"}


@admin_router.post("/settings/prompts")
async def update_prompts(
    data: dict,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Update system/user/repair prompts."""
    for key in ["system_prompt", "user_template", "repair_prompt"]:
        if key in data:
            await _upsert_setting(db, key, data[key], admin.id)
    await db.commit()
    return {"status": "ok"}


# ── Plans ────────────────────────────────────────────────────

@admin_router.get("/plans")
async def list_plans(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    result = await db.execute(select(Plan).order_by(Plan.created_at))
    plans = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "code": p.code,
            "name": p.name,
            "price": float(p.price) if p.price else 0,
            "currency": p.currency,
            "limits": p.limits_json,
            "is_active": p.is_active,
        }
        for p in plans
    ]


@admin_router.post("/plans")
async def upsert_plan(
    data: dict,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    code = data.get("code")
    if not code:
        raise HTTPException(400, "code is required")

    result = await db.execute(select(Plan).where(Plan.code == code))
    plan = result.scalar_one_or_none()

    if plan is None:
        plan = Plan(code=code)
        db.add(plan)

    plan.name = data.get("name", code)
    plan.price = data.get("price", 0)
    plan.currency = data.get("currency", "USD")
    plan.limits_json = data.get("limits", {})
    plan.is_active = data.get("is_active", True)

    await db.commit()
    return {"status": "ok", "plan_id": str(plan.id)}


@admin_router.post("/settings/affiliate")
async def update_affiliate_settings(
    data: dict,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Update affiliate program settings."""
    for key in ["affiliate_commission_rate", "affiliate_min_withdrawal"]:
        if key in data:
            await _upsert_setting(db, key, str(data[key]), admin.id)
    await db.commit()
    return {"status": "ok"}


@admin_router.post("/settings/payments")
async def update_payment_settings(
    data: dict,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Update payment gateway settings (secrets)."""
    for key in ["yoomoney_shop_id", "yoomoney_secret", "robokassa_merchant_id", "robokassa_password_1", "robokassa_password_2", "cryptobot_token"]:
        if key in data and data[key]:
            await _upsert_setting(db, key, data[key], admin.id, is_secret=True)
    await db.commit()
    return {"status": "ok"}
@admin_router.get("/payments")
async def list_payments(
    user_id: Optional[UUID] = Query(None),
    offset: int = Query(0),
    limit: int = Query(50),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    q = select(Payment).order_by(desc(Payment.created_at))
    if user_id:
        q = q.where(Payment.user_id == user_id)
    q = q.offset(offset).limit(limit)

    result = await db.execute(q)
    payments = result.scalars().all()

    return [
        {
            "id": str(p.id),
            "user_id": str(p.user_id),
            "provider": p.provider,
            "amount": float(p.amount),
            "currency": p.currency,
            "status": p.status,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "provider_payment_id": p.provider_payment_id,
        }
        for p in payments
    ]
