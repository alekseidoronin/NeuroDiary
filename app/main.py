"""
Entry point — FastAPI + aiogram with dual mode (webhook / polling).
"""

from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Update
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

from app.config import settings
from app.db.engine import engine
from app.db.models import Base
from app.api.webhook import router as tg_router
from app.api.admin import admin_router

# ── Logging ──────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# ── Bot & Dispatcher ────────────────────────────────────────

from app.core.bot import bot, dp
dp.include_router(tg_router)


# ── Lifecycle (lifespan) ────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ensured")

    # Check if we should start polling (if not in webhook mode and not running under uvicorn worker)
    # Actually, let's just use a simple check: if WEBHOOK_HOST is not set, we might be in polling mode
    if settings.WEBHOOK_HOST:
        url = settings.webhook_url
        await bot.set_webhook(url, drop_pending_updates=True)
        logger.info("Webhook set: %s", url)
    else:
        # We start polling only if explicitly requested via CLI or if this is the main process
        # But here we can just check a global flag set in __main__
        if getattr(app.state, "start_polling", False):
            # Set commands for polling mode too
            from aiogram.types import BotCommand
            await bot.set_my_commands([
                BotCommand(command="start", description="🏠 Главное меню"),
                BotCommand(command="settings", description="⚙️ Настройки"),
                BotCommand(command="help", description="❓ Помощь"),
            ])
            asyncio.create_task(dp.start_polling(bot, drop_pending_updates=True))
            logger.info("Bot polling started in background")
        else:
            logger.info("Polling not started (web mode)")

    from app.services.scheduler import setup_scheduler
    app.state.scheduler = setup_scheduler()

    yield

    # Shutdown
    if settings.WEBHOOK_HOST:
        await bot.delete_webhook()
    await bot.session.close()
    await engine.dispose()
    logger.info("Shutdown complete")


# ── FastAPI app ─────────────────────────────────────────────

app = FastAPI(
    title="DiaryBot",
    version="2.0.0",
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
)

# CORS for Mini App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Admin API
app.include_router(admin_router)

import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_DIR = os.path.join(BASE_DIR, "admin-app", "dist")

# Admin Mini App Static Files
if os.path.exists(DIST_DIR):
    app.mount(
        "/admin-app",
        StaticFiles(directory=DIST_DIR, html=True),
        name="admin-app"
    )
else:
    logger.warning("Admin Mini App build not found at %s", DIST_DIR)


# ── Webhook endpoint ────────────────────────────────────────

@app.post(settings.WEBHOOK_PATH)
async def telegram_webhook(request: Request) -> Response:
    data = await request.json()
    update = Update.model_validate(data, context={"bot": bot})
    await dp.feed_update(bot=bot, update=update)
    return Response(status_code=200)


# ── Health check ─────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "bot": "DiaryCode", "version": "2.0.0"}

# ── CLI ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "polling"

    if mode == "polling":
        app.state.start_polling = True
        uvicorn.run(app, host="0.0.0.0", port=8000)
    elif mode == "webhook":
        app.state.start_polling = False
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=settings.WEBHOOK_PORT,
            log_level=settings.LOG_LEVEL.lower(),
        )
    else:
        print(f"Unknown mode: {mode}")
        print("Usage: python -m app.main [polling|webhook]")
        sys.exit(1)
