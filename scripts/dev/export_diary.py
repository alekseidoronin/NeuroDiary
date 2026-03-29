#!/usr/bin/env python3
"""Export all journal entries for a user to HTML. Run from repo root: PYTHONPATH=. python scripts/dev/export_diary.py ..."""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.db.engine import async_session
from app.db.models import JournalEntry, User


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Export diary entries to HTML")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--user-id", type=str, help="users.id (UUID)")
    g.add_argument("--tg-user-id", type=int, help="Telegram user id")
    p.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("diary_export.html"),
        help="output HTML file (default: diary_export.html)",
    )
    return p.parse_args()


async def export_html(user_id: str | None, tg_user_id: int | None, output: Path) -> None:
    async with async_session() as db:
        user = None
        if user_id:
            user = await db.scalar(select(User).where(User.id == user_id))
        if user is None and tg_user_id is not None:
            user = await db.scalar(select(User).where(User.tg_user_id == tg_user_id))
        if not user:
            print("User not found")
            return

        result = await db.execute(
            select(JournalEntry)
            .where(JournalEntry.user_id == user.id)
            .order_by(JournalEntry.entry_date.desc())
        )
        entries = result.scalars().all()

        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Diary Export</title>
            <style>
                body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }
                .entry { margin-bottom: 40px; border-bottom: 1px solid #ccc; padding-bottom: 20px; }
                .date { font-weight: bold; color: #555; }
                h1, h2, h3 { color: #333; }
                ul { padding-left: 20px; }
            </style>
        </head>
        <body>
            <h1>История дневника</h1>
        """

        for e in entries:
            text = e.final_diary_text or ""
            text = text.replace("**", "<b>").replace("**", "</b>")
            text = text.replace("- ", "<li>").replace("\n", "<br>")

            html += f"""
            <div class="entry">
                <div class="date">{e.entry_date}</div>
                <div class="content">{text}</div>
            </div>
            """

        html += "</body></html>"

        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(html, encoding="utf-8")
        print(f"Exported {len(entries)} entries to {output.resolve()}")


def main() -> None:
    args = parse_args()
    asyncio.run(export_html(args.user_id, args.tg_user_id, args.output))


if __name__ == "__main__":
    main()
