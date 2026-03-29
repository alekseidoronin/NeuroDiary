"""
Split long diary HTML into Telegram-sized parts (4096 chars each). Pure functions — no aiogram.
"""

from __future__ import annotations

TG_MSG_LIMIT = 4096
_SPLIT_FOOTER_RESERVE = 56


def split_long_line(line: str, max_len: int) -> list[str]:
    if len(line) <= max_len:
        return [line]
    out: list[str] = []
    rest = line
    while rest:
        if len(rest) <= max_len:
            out.append(rest)
            break
        window = rest[:max_len]
        br = window.rfind("\n")
        if br < max_len // 2:
            br = window.rfind(" ")
        if br < max_len // 2:
            br = max_len
        piece = rest[:br].rstrip()
        if not piece:
            piece = rest[:max_len]
            br = max_len
        out.append(piece)
        rest = rest[br:].lstrip()
    return out


def _build_body_chunks(text: str, content_limit: int) -> list[str]:
    lines = text.split("\n")
    chunks: list[str] = []
    current_chunk: list[str] = []
    current_len = 0

    for line in lines:
        for segment in split_long_line(line, content_limit):
            seg_len = len(segment)
            extra = 1 if current_chunk else 0
            if current_len + extra + seg_len > content_limit and current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = [segment]
                current_len = seg_len
            else:
                current_chunk.append(segment)
                current_len += extra + seg_len

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    fixed: list[str] = []
    for ch in chunks:
        if len(ch) <= content_limit:
            fixed.append(ch)
        else:
            fixed.extend(split_long_line(ch, content_limit))
    return fixed


def split_for_telegram(text: str, limit: int = TG_MSG_LIMIT) -> list[str]:
    """As many parts as needed; each part length ≤ limit."""
    if len(text) <= limit:
        return [text]

    for reserve in (_SPLIT_FOOTER_RESERVE, 80, 120, 192, 320, 512):
        content_limit = max(200, limit - reserve)
        chunks = _build_body_chunks(text, content_limit)
        n = len(chunks)
        if n <= 1:
            return chunks
        footers = [f"\n\n<i>Часть {i + 1}/{n}</i>" for i in range(n)]
        parts = [chunks[i] + footers[i] for i in range(n)]
        if all(len(p) <= limit for p in parts):
            return parts

    out: list[str] = []
    for i in range(0, len(text), limit):
        out.append(text[i : i + limit])
    return out
