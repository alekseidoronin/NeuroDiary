"""Tests for Telegram message chunking (no aiogram)."""

from app.services.telegram_chunk import TG_MSG_LIMIT, split_for_telegram


def test_short_unchanged():
    s = "hello"
    assert split_for_telegram(s) == [s]


def test_each_part_within_limit():
    body = "x" * 12000
    parts = split_for_telegram(body)
    assert len(parts) >= 3
    assert all(len(p) <= TG_MSG_LIMIT for p in parts)


def test_multiline_preserves_order():
    lines = [f"line{i:04d}" for i in range(500)]
    body = "\n".join(lines)
    parts = split_for_telegram(body)
    blob = "".join(parts)
    for ln in lines[::50]:
        assert ln in blob
    assert all(len(p) <= TG_MSG_LIMIT for p in parts)
