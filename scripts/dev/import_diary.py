#!/usr/bin/env python3
"""
Import diary entries from a markdown/text archive into PostgreSQL.

Run from repository root:
  PYTHONPATH=. python scripts/dev/import_diary.py --text-file scripts/dev/data/import_payload.txt --user-id <uuid>

Or use Telegram user id:
  PYTHONPATH=. python scripts/dev/import_diary.py --tg-user-id 123456789
"""
from __future__ import annotations

import argparse
import asyncio
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.db.engine import async_session
from app.db.models import JournalEntry, User

DEFAULT_PAYLOAD = Path(__file__).resolve().parent / "data" / "import_payload.txt"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Import diary archive from file")
    p.add_argument(
        "--text-file",
        type=Path,
        default=DEFAULT_PAYLOAD,
        help=f"path to archive text (default: {DEFAULT_PAYLOAD})",
    )
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--user-id", type=str, help="users.id UUID")
    g.add_argument("--tg-user-id", type=int, help="Telegram user id")
    return p.parse_args()


async def run_import(text: str, user_id: str | None, tg_user_id: int | None) -> None:
    async with async_session() as db:
        user = None
        if user_id:
            user = await db.scalar(select(User).where(User.id == user_id))
        if user is None and tg_user_id is not None:
            user = await db.scalar(select(User).where(User.tg_user_id == tg_user_id))
        if not user:
            print("User not found")
            return

        chunks: list[tuple[str, str]] = []
        current_chunk: list[str] = []
        current_date_str: str | None = None

        lines = text.strip().split("\n")
        date_pattern = re.compile(r"(\d{4}\.\d{2}\.\d{2})")

        for line in lines:
            match = date_pattern.search(line)
            if match and (line.startswith("#") or line.strip().startswith("202") or line.strip().startswith("203")):
                if current_chunk and current_date_str:
                    chunks.append((current_date_str, "\n".join(current_chunk).strip()))
                current_date_str = match.group(1)
                current_chunk = [line]
            else:
                if current_date_str:
                    current_chunk.append(line)

        if current_chunk and current_date_str:
            chunks.append((current_date_str, "\n".join(current_chunk).strip()))

        print(f"Found {len(chunks)} entries to import.")

        count = 0
        for date_str, text_content in chunks:
            try:
                dt = datetime.strptime(date_str, "%Y.%m.%d").date()
            except ValueError:
                print(f"Skipping bad date: {date_str}")
                continue

            entry = JournalEntry(
                user_id=user.id,
                source_message_id=None,
                input_type="import",
                entry_date=dt,
                entry_time="12:00",
                raw_input_text="Imported from archive",
                transcript_text=None,
                final_diary_text=text_content,
                status="ok",
                is_admin_entry=False,
            )
            db.add(entry)
            count += 1

        await db.commit()
        print(f"Imported {count} entries successfully.")


def main() -> None:
    args = parse_args()
    path = args.text_file
    if not path.is_file():
        print(f"File not found: {path}", file=sys.stderr)
        print("Create it from your archive or copy from a previous import_diary.py backup.", file=sys.stderr)
        sys.exit(1)
    text = path.read_text(encoding="utf-8")
    asyncio.run(run_import(text, args.user_id, args.tg_user_id))


if __name__ == "__main__":
    main()
