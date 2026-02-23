"""
Event logging service — writes to the events table.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Event

logger = logging.getLogger(__name__)


async def log_event(
    db: AsyncSession,
    event_name: str,
    user_id: Optional[UUID] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    """Insert a row into the events table."""
    event = Event(
        user_id=user_id,
        event_name=event_name,
        payload=payload or {},
    )
    db.add(event)
    await db.flush()
    logger.debug("Event logged: %s (user=%s)", event_name, user_id)
