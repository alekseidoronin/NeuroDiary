"""
Settings service — merges DB settings with .env defaults.
Allows for runtime changes of prompts and API keys without restart.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as env_settings
from app.db.models import BotSettings
from app.services.crypto import decrypt_value

if TYPE_CHECKING:
    from app.db.models import User

logger = logging.getLogger(__name__)

class DynamicSettings:
    """Helper to fetch settings with fallback to app.config."""

    def __init__(self, db: AsyncSession):
        self._db = db
        self._cache = {}

    async def get(self, key: str, default: Any = None) -> Any:
        """Get a setting from DB, fallback to environment variable."""
        # 1. Check local cache (per request)
        if key in self._cache:
            return self._cache[key]

        # 2. Check DB
        result = await self._db.execute(select(BotSettings).where(BotSettings.key == key))
        obj = result.scalar_one_or_none()

        if obj:
            if obj.is_secret:
                value = decrypt_value(obj.encrypted_value)
            else:
                value = obj.value
            # Only use DB value if it's non-empty; otherwise fall through to .env
            if value:
                self._cache[key] = value
                return value

        # 3. Fallback to .env (Settings class)
        # Convert lowercase key to uppercase for env lookup
        env_key = key.upper()
        val = getattr(env_settings, env_key, default)
        self._cache[key] = val
        return val

    # ── Quick Accessors ──────────────────────────────────────

    async def get_system_prompt(self, user: Optional[User] = None) -> str:
        if user and user.custom_system_prompt:
            return user.custom_system_prompt
        from app.services.prompts import SYSTEM_PROMPT
        return await self.get("system_prompt", SYSTEM_PROMPT)

    async def get_user_template(self, user: Optional[User] = None) -> str:
        if user and user.custom_user_template:
            return user.custom_user_template
        from app.services.prompts import USER_TEMPLATE
        return await self.get("user_template", USER_TEMPLATE)

    async def get_repair_prompt(self) -> str:
        from app.services.prompts import REPAIR_PROMPT
        return await self.get("repair_prompt", REPAIR_PROMPT)

    async def get_llm_provider(self) -> str:
        return await self.get("llm_provider", env_settings.LLM_PROVIDER)

    async def get_stt_provider(self) -> str:
        return await self.get("stt_provider", env_settings.STT_PROVIDER)

    async def get_llm_model(self, provider: str) -> str:
        # Try generic key first (set by admin panel)
        val = await self.get("llm_model")
        if val:
            return val

        if provider == "gemini":
            return await self.get("gemini_model", env_settings.GEMINI_MODEL)
        return await self.get("openai_model", env_settings.OPENAI_MODEL)

    async def get_llm_api_key(self, provider: str) -> str:
        if provider == "gemini":
            return await self.get("gemini_api_key", env_settings.GEMINI_API_KEY)
        return await self.get("openai_api_key", env_settings.OPENAI_API_KEY)

    async def get_stt_api_key(self, provider: str) -> str:
        if provider == "assemblyai":
            return await self.get("assemblyai_api_key", env_settings.ASSEMBLYAI_API_KEY)
        return ""
