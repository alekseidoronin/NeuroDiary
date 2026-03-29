import logging
from typing import Dict, Any

from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import select, update
import json

from app.db.engine import async_session
from app.db.models import JournalEntry
from app.core.bot import bot
from sqlalchemy.orm import selectinload
from app.services.telegram_ui import build_entry_actions_kb

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Editor UI ──────────────────────────────────────────────────

EDITOR_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Редактирование записи</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        :root {
            --bg-color: var(--tg-theme-bg-color, #ffffff);
            --text-color: var(--tg-theme-text-color, #000000);
            --hint-color: var(--tg-theme-hint-color, #999999);
            --button-color: var(--tg-theme-button-color, #3390ec);
            --button-text-color: var(--tg-theme-button-text-color, #ffffff);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }

        body {
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding: 16px;
            display: flex;
            flex-direction: column;
            height: 100vh;
            box-sizing: border-box;
        }

        h2 {
            margin-top: 0;
            font-size: 18px;
            color: var(--text-color);
        }

        textarea {
            width: 100%;
            flex-grow: 1;
            padding: 12px;
            font-size: 16px;
            font-family: inherit;
            border: 1px solid var(--hint-color);
            border-radius: 8px;
            background-color: var(--bg-color);
            color: var(--text-color);
            resize: none;
            box-sizing: border-box;
            outline: none;
        }

        textarea:focus {
            border-color: var(--button-color);
        }

        #loading {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 16px;
            color: var(--hint-color);
            display: none;
        }
    </style>
</head>
<body>

    <div id="loading">Загрузка...</div>
    <textarea id="editor" style="display: none;"></textarea>

    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();

        const entryId = "{{ENTRY_ID}}";
        const editor = document.getElementById("editor");
        const loading = document.getElementById("loading");

        // Load entry content
        async function fetchEntry() {
            loading.style.display = "block";
            try {
                const response = await fetch(`/webapp/api/entry/${entryId}`);
                if (!response.ok) throw new Error("Server error");
                
                const data = await response.json();
                editor.value = data.text;
                
                loading.style.display = "none";
                editor.style.display = "block";
                
                // Show MainButton
                tg.MainButton.text = "СОХРАНИТЬ";
                tg.MainButton.show();
            } catch (error) {
                loading.innerText = "Ошибка загрузки данных.";
            }
        }

        // Save entry content
        tg.MainButton.onClick(async () => {
            const newText = editor.value.trim();
            if (!newText) {
                tg.showAlert("Текст не может быть пустым.");
                return;
            }

            tg.MainButton.showProgress();

            try {
                const response = await fetch(`/webapp/api/entry/${entryId}`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ text: newText })
                });

                if (response.ok) {
                    tg.close();
                } else {
                    const data = await response.json();
                    tg.showAlert(data.detail || "Не удалось сохранить изменения.");
                }
            } catch (error) {
                tg.showAlert("Ошибка соединения.");
            } finally {
                tg.MainButton.hideProgress();
            }
        });

        fetchEntry();
    </script>
</body>
</html>
"""

# ── API Routes ─────────────────────────────────────────────────

@router.get("/webapp/edit/{entry_id}", response_class=HTMLResponse)
async def webapp_edit_form(entry_id: str):
    """Serves the frontend Application for Telegram Web App."""
    html = EDITOR_HTML.replace("{{ENTRY_ID}}", entry_id)
    return HTMLResponse(content=html)


async def _get_entry_text_impl(entry_id: str):
    """API called by Web App to retrieve existing text to pre-fill the textarea."""
    async with async_session() as db:
        result = await db.execute(select(JournalEntry).where(JournalEntry.id == entry_id))
        entry = result.scalar_one_or_none()
        
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        return {"text": entry.final_diary_text or ""}


async def _save_entry_text_impl(entry_id: str, request: Request):
    """API called by Web App when user clicks 'Save'. Updates DB and Telegram Chat Message in-place."""
    data = await request.json()
    new_text = data.get("text")
    
    if not new_text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    async with async_session() as db:
        result = await db.execute(
            select(JournalEntry)
            .options(selectinload(JournalEntry.user))
            .where(JournalEntry.id == entry_id)
        )
        entry = result.scalar_one_or_none()
        
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        # 1. Update text in Database
        await db.execute(
            update(JournalEntry)
            .where(JournalEntry.id == entry_id)
            .values(final_diary_text=new_text)
        )
        await db.commit()
        
        # 2. Rebuild the inline keyboard with WebApp button
        kb = build_entry_actions_kb(str(entry_id))

        # 3. Update Telegram: first bubble is edited, extra chunks sent as new messages (no part limit)
        if entry.bot_message_id and entry.user and entry.user.tg_user_id:
            from app.api.webhook import deliver_diary_chunks_to_chat
            from app.services.telegram_chunk import split_for_telegram

            parts = split_for_telegram(new_text)
            try:
                await deliver_diary_chunks_to_chat(
                    bot=bot,
                    chat_id=entry.user.tg_user_id,
                    parts=parts,
                    reply_markup=kb,
                    edit_message_id=entry.bot_message_id,
                )
            except Exception as e:
                logger.warning("deliver_diary_chunks_to_chat (webapp save) failed: %s", e, exc_info=True)
                try:
                    head = (parts[0] if parts else new_text)[:4096]
                    sent = await bot.send_message(
                        chat_id=entry.user.tg_user_id,
                        text=head,
                        reply_markup=kb,
                    )
                    await db.execute(
                        update(JournalEntry)
                        .where(JournalEntry.id == entry.id)
                        .values(bot_message_id=sent.message_id)
                    )
                    await db.commit()
                except Exception as e2:
                    logger.warning("Fallback send after webapp save failed: %s", e2)

    return {"status": "success"}


# New canonical paths (works behind /webapp* reverse-proxy rules)
@router.get("/webapp/api/entry/{entry_id}")
async def get_entry_text_webapp(entry_id: str):
    return await _get_entry_text_impl(entry_id)


@router.post("/webapp/api/entry/{entry_id}")
async def save_entry_text_webapp(entry_id: str, request: Request):
    return await _save_entry_text_impl(entry_id, request)


# Backward-compatible aliases
@router.get("/api/webapp/entry/{entry_id}")
async def get_entry_text(entry_id: str):
    return await _get_entry_text_impl(entry_id)


@router.post("/api/webapp/entry/{entry_id}")
async def save_entry_text(entry_id: str, request: Request):
    return await _save_entry_text_impl(entry_id, request)
