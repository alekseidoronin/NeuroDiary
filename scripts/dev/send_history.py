#!/usr/bin/env python3
"""Send all journal entries to user's Telegram. Run from repo root: PYTHONPATH=. python scripts/dev/send_history.py ..."""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aiogram import Bot
from sqlalchemy import select

from app.config import settings
from app.db.engine import async_session
from app.db.models import JournalEntry, User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Send all entries to user's Telegram")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--user-id", type=str, help="users.id (UUID)")
    g.add_argument("--tg-user-id", type=int, help="Telegram user id")
    p.add_argument("--delay", type=float, default=0.5, help="seconds between messages")
    return p.parse_args()


async def send_history(user_id: str | None, tg_user_id: int | None, delay: float) -> None:
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)

    async with async_session() as db:
        user = None
        if user_id:
            user = await db.scalar(select(User).where(User.id == user_id))
        if user is None and tg_user_id is not None:
            user = await db.scalar(select(User).where(User.tg_user_id == tg_user_id))
        if not user:
            print("User not found")
            await bot.session.close()
            return

        result = await db.execute(
            select(JournalEntry)
            .where(JournalEntry.user_id == user.id)
            .order_by(JournalEntry.entry_date)
        )
        entries = result.scalars().all()

        print(f"Found {len(entries)} entries. Sending to {user.tg_user_id}...")

        for entry in entries:
            text = entry.final_diary_text
            if not text:
                continue
            try:
                await bot.send_message(
                    chat_id=user.tg_user_id,
                    text=text,
                    parse_mode="HTML",
                )
                print(f"Sent entry for {entry.entry_date}")
                await asyncio.sleep(delay)
            except Exception as e:
                print(f"Failed to send entry {entry.entry_date}: {e}")

    await bot.session.close()
    print("Done sending history.")


def main() -> None:
    args = parse_args()
    asyncio.run(send_history(args.user_id, args.tg_user_id, args.delay))


if __name__ == "__main__":
    main()
