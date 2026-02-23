"""
Scheduler for background tasks:
1. Smart Reminders (check non-active users).
2. Weekly Summaries (every Sunday).
"""

import logging
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.db.engine import async_session
from app.db.models import User, JournalEntry
from app.core.bot import bot
from app.services.summarizer import generate_weekly_summary
from aiogram.enums import ParseMode

logger = logging.getLogger(__name__)

async def send_smart_reminders():
    """Check users who didn't write for 24+ hours."""
    async with async_session() as db:
        one_day_ago = datetime.now() - timedelta(hours=24)
        # Users who were seen more than 24h ago and are active
        q = select(User).where(
            and_(
                User.last_seen_at < one_day_ago,
                User.status == 'active'
            )
        )
        result = await db.execute(q)
        users = result.scalars().all()

        for u in users:
            try:
                await bot.send_message(
                    chat_id=u.tg_user_id,
                    text="👋 Привет! Давно не виделись. Как прошел твой день? Расскажи мне, я всё запишу в твой дневник. ✨"
                )
                # Update last_seen_at so we don't spam every hour
                u.last_seen_at = datetime.now() 
                await db.commit()
            except Exception as e:
                logger.warning(f"Failed to send reminder to {u.tg_user_id}: {e}")

async def send_weekly_summaries():
    """
    Check all users. If it is Sunday and their preferred time in their timezone, send summary.
    Runs every hour.
    """
    import pytz
    
    async with async_session() as db:
        # Get all users with summaries enabled
        # We could filter by timezone in SQL but python logic is easier for variable logic
        q = select(User).where(User.weekly_summary_enabled == True)
        result = await db.execute(q)
        users = result.scalars().all()

        current_utc = datetime.now(pytz.utc)

        for u in users:
            try:
                # 1. Get user timezone
                try:
                    tz = pytz.timezone(u.timezone or "UTC")
                except pytz.UnknownTimeZoneError:
                    tz = pytz.utc
                
                user_now = current_utc.astimezone(tz)
                
                # 2. Check if it is Sunday (weekday 6)
                if user_now.weekday() != 6:
                    continue
                
                # 3. Check if current hour matches user preference
                # u.notification_time is "HH:MM", default "21:00"
                pref_time = u.notification_time or "21:00"
                pref_hour = int(pref_time.split(':')[0])
                
                # We run this job every hour (at :00 minute ideally).
                # Check if user_now.hour matches.
                if user_now.hour == pref_hour:
                    logger.info(f"Sending weekly summary to {u.tg_user_id} (Local time: {user_now})")
                    summary = await generate_weekly_summary(db, u)
                    await bot.send_message(
                        chat_id=u.tg_user_id,
                        text=f"📊 <b>Твой итог недели готов!</b>\n\n{summary}",
                        parse_mode=ParseMode.HTML
                    )
            except Exception as e:
                logger.error(f"Failed to send weekly summary to {u.tg_user_id}: {e}")

def setup_scheduler():
    scheduler = AsyncIOScheduler()
    
    # 1. Smart reminders every 6 hours
    scheduler.add_job(send_smart_reminders, 'interval', hours=6)
    
    # 2. Weekly summaries check every hour
    # We use cron to run at minute 0 of every hour
    scheduler.add_job(
        send_weekly_summaries, 
        CronTrigger(minute=0)
    )
    
    scheduler.start()
    logger.info("Scheduler started: Smart Reminders (6h), Weekly Summaries (Hourly Check)")
    return scheduler
