"""
Centralised settings loaded from environment / .env file.
Uses pydantic-settings for validation.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Telegram ─────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str

    # ── Webhook ──────────────────────────────────────────────
    WEBHOOK_HOST: str = ""
    WEBHOOK_PATH: str = "/webhook/telegram"
    WEBHOOK_PORT: int = 8443

    @property
    def webhook_url(self) -> str:
        return f"{self.WEBHOOK_HOST}{self.WEBHOOK_PATH}"

    @property
    def public_base_url(self) -> str:
        if self.WEBHOOK_HOST:
            return self.WEBHOOK_HOST
        if self.MINI_APP_URL:
            import urllib.parse
            parsed = urllib.parse.urlparse(self.MINI_APP_URL)
            return f"{parsed.scheme}://{parsed.netloc}"
        return "https://diary.144.217.12.20.nip.io"

    # ── Database (Postgres) ──────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://diary:diary@localhost:5432/diarybot"

    # ── Redis (task queue) ───────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── AssemblyAI (STT) ─────────────────────────────────────
    ASSEMBLYAI_API_KEY: str = ""

    # ── OpenAI ───────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    # ── Gemini ───────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # ── Active providers (default) ───────────────────────────
    STT_PROVIDER: str = "assemblyai"          # assemblyai
    LLM_PROVIDER: str = "gemini"              # gemini | openai

    # ── LLM tuning ──────────────────────────────────────────
    LLM_TEMPERATURE: float = 0.7
    # Single-call output budget; continuation rounds add more if model hits the cap.
    LLM_MAX_TOKENS: int = 8192
    # DB/admin may set llm_max_tokens lower — we never go below this for diary generation.
    LLM_OUTPUT_TOKEN_FLOOR: int = 8192

    # ── Voice limits ─────────────────────────────────────────
    MAX_VOICE_DURATION_SECONDS: int = 300

    # ── Admin ────────────────────────────────────────────────
    ADMIN_TG_USER_IDS: str = ""               # comma-separated
    ADMIN_PASSWORD: str = "admin123"           # password for non-TG admin login

    # ── Encryption key for storing API keys in DB ────────────
    ENCRYPTION_KEY: str = ""                  # Fernet key (32-byte base64)

    # ── Mini App ─────────────────────────────────────────────
    MINI_APP_URL: str = ""                    # URL where Mini App is hosted

    # ── Defaults ─────────────────────────────────────────────
    DEFAULT_TIMEZONE: str = "Asia/Dubai"
    DEFAULT_LOCALE: str = "ru"
    LOG_LEVEL: str = "INFO"

    # ── Trial ────────────────────────────────────────────────
    TRIAL_ENTRIES_PER_DAY: int = 5
    TRIAL_STT_SECONDS_PER_DAY: int = 300

    @property
    def admin_user_ids(self) -> set:
        if not self.ADMIN_TG_USER_IDS:
            return set()
        return {int(x.strip()) for x in self.ADMIN_TG_USER_IDS.split(",") if x.strip()}


settings = Settings()
