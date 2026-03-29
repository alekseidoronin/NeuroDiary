from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types.web_app_info import WebAppInfo

from app.config import settings


def build_entry_actions_kb(entry_id: str) -> InlineKeyboardMarkup:
    """Unified inline keyboard for entry actions."""
    webapp_url = f"{settings.public_base_url}/webapp/edit/{entry_id}"
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✏️ Редактировать", web_app=WebAppInfo(url=webapp_url)),
        InlineKeyboardButton(text="🔊 Озвучить", callback_data=f"tts:{entry_id}"),
    ]])
