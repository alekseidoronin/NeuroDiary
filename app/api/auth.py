"""
Telegram Mini App authentication — validates init data from Telegram.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Optional
from urllib.parse import parse_qs, unquote

import json
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.engine import get_db
from app.db.models import User

logger = logging.getLogger(__name__)


def _validate_init_data(init_data: str, bot_token: str) -> Optional[dict]:
    """
    Validate Telegram Mini App init data.
    See: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    parsed = parse_qs(init_data, keep_blank_values=True)

    # Get hash
    received_hash = parsed.get("hash", [None])[0]
    if not received_hash:
        return None

    # Build data check string (sorted, without hash)
    data_pairs = []
    for key, values in parsed.items():
        if key == "hash":
            continue
        data_pairs.append(f"{key}={values[0]}")
    data_pairs.sort()
    data_check_string = "\n".join(data_pairs)

    # HMAC-SHA256 with "WebAppData" as key
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        return None

    # Extract user info
    user_data_raw = parsed.get("user", [None])[0]
    if user_data_raw:
        return json.loads(unquote(user_data_raw))
    return {}


async def get_admin_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency — extracts and validates Telegram Mini App auth.
    Returns the User if they are an admin.
    """
    # Import here to avoid circular dependencies if any, or at top level if clean
    from app.services.rate_limit import check_admin_rate_limit, record_failed_login, reset_failed_login

    init_data = request.headers.get("X-Telegram-Init-Data", "")
    admin_pass = request.headers.get("X-Admin-Password", "")

    # 1. Check Rate Limit (IP based) regardless of auth method to prevent abuse
    await check_admin_rate_limit(request)

    # 2. Password-based login (for browser access)
    if admin_pass:
        if admin_pass == settings.ADMIN_PASSWORD:
            # Password correct
            # Find first admin in DB
            result = await db.execute(select(User).where(User.role == "admin").limit(1))
            user = result.scalar_one_or_none()
            if user:
                # Success! Reset fail counter
                await reset_failed_login(request)
                return user
            # Password correct but no admin user in DB? Still treat as success for rate limiter?
            # Or fail? Let's treat as success auth-wise but fail logical-wise.
            # Actually, without user we can't let them in.
            # But the password WAS correct. So don't ban them.
        else:
            # Password incorrect
            await record_failed_login(request)
            # If password was provided but wrong, we deny access immediately to prevent brute force
            # even if init_data is present (which is unlikely in same request)
            raise HTTPException(status_code=401, detail="Invalid admin password")

    if not init_data:
        raise HTTPException(status_code=401, detail="Missing Telegram init data")

    tg_user = _validate_init_data(init_data, settings.TELEGRAM_BOT_TOKEN)
    if tg_user is None:
        raise HTTPException(status_code=401, detail="Invalid Telegram init data")

    tg_user_id = tg_user.get("id")
    if not tg_user_id:
        raise HTTPException(status_code=401, detail="No user ID in init data")

    # Find user in DB
    result = await db.execute(select(User).where(User.tg_user_id == tg_user_id))
    user = result.scalar_one_or_none()

    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    return user
