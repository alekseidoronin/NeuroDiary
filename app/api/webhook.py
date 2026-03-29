"""
Telegram webhook handler — receives update, normalises, runs pipeline.
"""

from __future__ import annotations

import logging
import time
from uuid import uuid4

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, ContentType, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, BufferedInputFile
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func

from app.config import settings
from app.db.engine import async_session
from app.db.models import User, TelegramUpdate, BotSettings, Subscription, JournalEntry
from app.dto.telegram import InputNormalizedDTO
from app.services.pipeline import process_message
from app.services.events import log_event
from app.services.prompts import SYSTEM_PROMPT
from app.services.billing import check_limits
from app.api.middleware import SubscriptionMiddleware
from app.services.tts import synthesize
from app.services.memory import get_last_entry_for_user
from app.services.telegram_ui import build_entry_actions_kb
from app.services.telegram_chunk import TG_MSG_LIMIT, split_for_telegram as _split_for_telegram

logger = logging.getLogger(__name__)

router = Router()
router.message.middleware(SubscriptionMiddleware())
router.callback_query.middleware(SubscriptionMiddleware())

from aiogram.fsm.state import State, StatesGroup

class UserStates(StatesGroup):
    setting_time = State()
    setting_prompt = State()

_tts_click_guard: dict[str, float] = {}


async def _send_one_part(
    bot: Bot,
    chat_id: int,
    text: str,
    *,
    parse_mode_first: bool = True,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """Send one chunk; on HTML parse error retry as plain text."""
    if parse_mode_first:
        try:
            await bot.send_message(chat_id, text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
            return
        except Exception as e:
            logger.warning("HTML send failed, retrying plain: %s", e)
    await bot.send_message(chat_id, text, reply_markup=reply_markup)


async def deliver_diary_chunks_to_chat(
    *,
    parts: list[str],
    reply_markup: InlineKeyboardMarkup | None = None,
    processing_msg: Message | None = None,
    bot: Bot | None = None,
    chat_id: int | None = None,
    edit_message_id: int | None = None,
) -> None:
    """Edit first bubble (or given message id) with parts[0], then send the rest.
    Keyboard goes on the last part if multi-part, else on the first. All parts are sent."""
    if not parts:
        return

    if processing_msg is not None:
        bot = processing_msg.bot
        chat_id = processing_msg.chat.id
        edit_message_id = processing_msg.message_id

    if bot is None or chat_id is None or edit_message_id is None:
        raise ValueError("deliver_diary_chunks_to_chat: need processing_msg or (bot, chat_id, edit_message_id)")

    n = len(parts)
    kb_first = reply_markup if n == 1 else None
    kb_last = reply_markup if n > 1 else None

    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=edit_message_id,
            text=parts[0],
            parse_mode=ParseMode.HTML,
            reply_markup=kb_first,
        )
    except Exception as e:
        logger.warning("edit_message_text HTML failed: %s", e)
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=edit_message_id,
                text=parts[0],
                reply_markup=kb_first,
            )
        except Exception as e2:
            logger.error("edit_message_text plain failed: %s", e2)
            raise

    for idx, part in enumerate(parts[1:]):
        is_last = idx == len(parts) - 2
        await _send_one_part(
            bot,
            chat_id,
            part,
            reply_markup=kb_last if is_last else None,
        )

# Local _check_limits was removed; using centralized logic from app.services.billing.

# ── Keyboards ───────────────────────────────────────────────

def get_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Настройки (Время/Стиль)", callback_data="settings_menu")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help_info")],
        [InlineKeyboardButton(text="🆘 Поддержка", url="https://t.me/Doronin_Al")],
    ])

def get_settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏰ Напоминание (Время)", callback_data="set_notif_time")],
        [InlineKeyboardButton(text="🎨 Изменить стиль (Промпт)", callback_data="set_summary_prompt")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_back")],
    ])

def get_prompt_settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Сбросить к стандартному", callback_data="prompt_reset")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="settings_menu")],
    ])

# ── /start ───────────────────────────────────────────────────

START_TEXT = """
👋 <b>Я — твой AI-дневник.</b>

Я помогаю сохранять важные моменты, структурируя твои мысли.

🎤 <b>Что я умею:</b>
1. Принимаю голосовые и текстовые заметки.
2. Превращаю их в структурированный дневник.
3. Сохраняю всё в надежном месте.

🎁 <b>Для новых пользователей доступно 5 бесплатных записей.</b>

👇 <b>Начни прямо сейчас — отправь мне сообщение!</b>
"""

@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    async with async_session() as db:
        user = await _ensure_user(db, message)
        if user.status in ("blocked", "deleted"):
             await message.answer("⛔ Ваш аккаунт отключен. Обратитесь к администратору @NeuroAlexD.")
             return

        await log_event(db, "user_started", user.id)
        await db.commit()

        # Check subscription explicitly here because middleware allows /start
        from app.api.middleware import REQUIRED_CHANNEL, CHANNEL_LINK, CHANNEL_NAME, redis
        from aiogram.enums import ChatMemberStatus

        is_subscribed = False
        # 1. Admin?
        if user.tg_user_id in settings.admin_user_ids:
            is_subscribed = True
        
        # 2. Redis check (if we enable it later)
        # 3. API Check
        if not is_subscribed:
            try:
                member = await message.bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user.tg_user_id)
                if member.status in [ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER, ChatMemberStatus.RESTRICTED]:
                    is_subscribed = True
            except Exception as e:
                logger.error(f"Manual sub check failed: {e}")

        if not is_subscribed:
            # Show Welcome + Subscribe Prompt
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📢 Подписаться на канал", url=CHANNEL_LINK)],
                [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub")]
            ])
            
            welcome_text = (
                f"👋 <b>Привет! Я — твой AI-дневник.</b>\n\n"
                "Я помогаю сохранять важные моменты и структурировать мысли.\n"
                "Чтобы начать работу, пожалуйста, подпишись на мой канал обновлений.\n\n"
                f'👉 <a href="{CHANNEL_LINK}">{CHANNEL_NAME}</a>'
            )
            await message.answer(welcome_text, parse_mode=ParseMode.HTML, reply_markup=kb, disable_web_page_preview=True)
            return

    # If subscribed, show Main Menu
    keyboard = get_main_keyboard()
    # Add memory button if user has older entries (could be slow, skip check for now)
    keyboard.inline_keyboard.insert(0, [InlineKeyboardButton(text="📅 Воспоминания (Этот день)", callback_data="memory_recall")])
    
    # Set bot menu button
    from aiogram.types import MenuButtonCommands, BotCommand
    await message.bot.set_my_commands([
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="settings", description="⚙️ Настройки"),
        BotCommand(command="help", description="❓ Помощь"),
        BotCommand(command="tts", description="🔊 Озвучить последнюю запись"),
    ])
    
    await message.answer(START_TEXT, parse_mode=ParseMode.HTML, reply_markup=keyboard)


@router.callback_query(F.data == "memory_recall")
async def cb_memory_recall(call: CallbackQuery):
    from datetime import date
    async with async_session() as db:
        user = await _ensure_user(db, call)
        
        today = date.today()
        # Find entries from previous years (same month & day)
        # Using simple python filtering after fetching candidates or raw SQL
        # Raw SQL is easier for date manipulation across years
        
        # "select * from journal_entries where user_id=... and status='ok' and 
        # extract(month from entry_date) = ... and extract(day from entry_date) = ... 
        # and extract(year from entry_date) < ..."
             
        from sqlalchemy import text
        
        # We use a raw query for simplicity with date functions
        query = text("""
            SELECT final_diary_text, entry_date 
            FROM journal_entries 
            WHERE user_id = :uid 
              AND status = 'ok'
              AND EXTRACT(MONTH FROM entry_date) = :m
              AND EXTRACT(DAY FROM entry_date) = :d
              AND EXTRACT(YEAR FROM entry_date) < :y
            ORDER BY entry_date DESC
            LIMIT 1
        """)
        
        result = await db.execute(query, {
            "uid": user.id,
            "m": today.month,
            "d": today.day,
            "y": today.year
        })
        row = result.fetchone()
        
        if not row:
             await call.answer("🔍 В этот день в прошлые годы записей не найдено.", show_alert=True)
             return

        entry_text = row[0]
        entry_date = row[1] # date object

        text = (
            f"🕰 <b>Воспоминание: {entry_date.strftime('%d.%m.%Y')}</b>\n\n"
            f"{entry_text}\n\n"
            f"<i>Как ты чувствуешь себя сейчас по сравнению с тем днем?</i>"
        )
        await call.message.answer(text, parse_mode=ParseMode.HTML)
        await call.answer()


@router.message(Command("tts"))
async def cmd_tts(message: Message) -> None:
    async with async_session() as db:
        user = await _ensure_user(db, message)
        if user.status in ("blocked", "deleted"):
            await message.answer("⛔ Ваш аккаунт отключен. Обратитесь к администратору @NeuroAlexD.")
            return

        entry = await get_last_entry_for_user(db, user.id)
        if not entry or not entry.final_diary_text:
            await message.answer("📭 Пока нечего озвучивать. Сначала отправь запись.")
            return

        try:
            audio = await synthesize(entry.final_diary_text, "ru")
            await message.answer_voice(
                BufferedInputFile(audio, filename=f"entry-{entry.id}.mp3"),
                caption="🔊 Озвучка последней записи",
            )
        except Exception as e:
            logger.error("TTS /tts failed: %s", e, exc_info=True)
            await message.answer("⚠️ Не удалось озвучить запись. Попробуйте позже.")


@router.callback_query(F.data.startswith("tts:"))
async def cb_tts_entry(call: CallbackQuery):
    try:
        _, entry_id = (call.data or "").split(":", 1)
    except ValueError:
        await call.answer("Некорректная команда.", show_alert=True)
        return

    # Ack callback quickly to reduce duplicate delivery/taps on slow TTS generation.
    await call.answer("⏳ Готовлю озвучку...")

    async with async_session() as db:
        user = await _ensure_user(db, call)
        guard_key = f"{user.id}:{entry_id}"
        now = time.monotonic()
        last_ts = _tts_click_guard.get(guard_key, 0.0)
        if now - last_ts < 3.0:
            return
        _tts_click_guard[guard_key] = now
        result = await db.execute(
            select(JournalEntry)
            .where(JournalEntry.id == entry_id)
            .where(JournalEntry.user_id == user.id)
            .where(JournalEntry.status == "ok")
            .limit(1)
        )
        entry = result.scalar_one_or_none()
        if not entry or not entry.final_diary_text:
            await call.message.answer("Запись не найдена или недоступна.")
            return

        try:
            audio = await synthesize(entry.final_diary_text, "ru")
            await call.message.answer_voice(
                BufferedInputFile(audio, filename=f"entry-{entry.id}.mp3"),
                caption="🔊 Озвучка записи",
            )
        except Exception as e:
            logger.error("TTS callback failed: %s", e, exc_info=True)
            await call.message.answer("Не удалось озвучить запись.")


@router.callback_query(F.data == "menu_back")
async def cb_menu_back(call: CallbackQuery):
    await call.message.edit_text(START_TEXT, parse_mode=ParseMode.HTML, reply_markup=get_main_keyboard())
    await call.answer()


@router.callback_query(F.data == "help_info")
async def cb_help_info(call: CallbackQuery):
    text = (
        "❓ <b>Как это работает?</b>\n\n"
        "1. Ты отправляешь мне <b>текст</b> или <b>голосовое</b>.\n"
        "2. Я обрабатываю это через мощную нейросеть.\n"
        "3. Я сохраняю результат в твою базу записей.\n\n"
        "Ты можешь выгрузить свои записи кнопкой «Экспорт».\n"
        "Настрой «Мой стиль», чтобы я писал так, как тебе нравится!"
    )
    await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_back")]
    ]))
    await call.answer()


@router.callback_query(F.data == "settings_menu")
async def cb_settings_menu(call: CallbackQuery):
    await call.message.edit_text("⚙️ <b>Меню настроек</b>", parse_mode=ParseMode.HTML, reply_markup=get_settings_keyboard())
    await call.answer()

@router.callback_query(F.data == "set_notif_time")
async def cb_set_notif_time(call: CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.setting_time)
    await call.message.answer("⏰ Введите время для итогов (формат HH:MM, например 21:00):")
    await call.answer()

@router.callback_query(F.data == "set_summary_prompt")
async def cb_set_summary_prompt(call: CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.setting_prompt)
    await call.message.answer("🎨 Введите инструкцию для стиля (например: 'Пиши кратко и с юмором'):")
    await call.answer()

@router.callback_query(F.data == "settings_prompt")
async def cb_settings_prompt(call: CallbackQuery):
    # Backward compatibility redirect
    await cb_settings_menu(call)


@router.callback_query(F.data == "prompt_reset")
async def cb_prompt_reset(call: CallbackQuery):
    async with async_session() as db:
        user = await _ensure_user(db, call)
        if user.status in ("blocked", "deleted"):
            await call.answer("⛔ Аккаунт отключен. Пишите @NeuroAlexD", show_alert=True)
            return
        user.custom_system_prompt = None
        await db.commit()
        await log_event(db, "user_prompt_reset", user.id)

    await call.answer("✅ Стиль сброшен к стандартному", show_alert=True)
    await cb_settings_prompt(call) # Refresh view


@router.callback_query(F.data == "export_entries")
async def cb_export_entries(call: CallbackQuery):
    await call.answer("🔍 Ищу записи...")
    # Reuse export logic but for callback
    from app.db.models import JournalEntry

    async with async_session() as db:
        user = await _ensure_user(db, call)
        if user.status in ("blocked", "deleted"):
            await call.answer("⛔ Аккаунт отключен. Пишите @NeuroAlexD", show_alert=True)
            return

        result = await db.execute(
            select(JournalEntry)
            .where(JournalEntry.user_id == user.id)
            .where(JournalEntry.status == "ok")
            .where(JournalEntry.is_admin_entry == False)
            .order_by(JournalEntry.created_at.desc())
            .limit(5)
        )
        entries = result.scalars().all()

    if not entries:
        await call.message.answer("📭 У тебя пока нет записей.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🗑 Скрыть", callback_data="delete_msg")]]))
        return

    for entry in reversed(entries):
        text = entry.final_diary_text or "(пусто)"
        try:
            await call.message.answer(text, parse_mode=ParseMode.HTML)
        except Exception:
            await call.message.answer(text)
    
    await call.message.answer("☝️ Это твои последние 5 записей.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🗑 Скрыть", callback_data="delete_msg")]]))


@router.callback_query(F.data == "delete_msg")
async def cb_delete_msg(call: CallbackQuery):
    await call.message.delete()
    await call.answer()


# ── Legacy Commands (Hidden) ────────────────────────────────

@router.message(Command("prompt"))
async def cmd_prompt(message: Message) -> None:
    async with async_session() as db:
        user = await _ensure_user(db, message)
        if user.role != "admin": return
        from app.services.settings import DynamicSettings
        ds = DynamicSettings(db)
        p = await ds.get_system_prompt()
        await message.answer(f"System Prompt:\n{p}")

@router.message(Command("set_prompt"))
async def cmd_set_prompt(message: Message) -> None:
    # Admin only
    async with async_session() as db:
        user = await _ensure_user(db, message)
        if user.role != "admin": return
        new_prompt = message.text.replace("/set_prompt", "", 1).strip()
        if not new_prompt:
             await message.answer("Empty prompt.")
             return
        from app.db.models import BotSettings
        res = await db.execute(select(BotSettings).where(BotSettings.key == "system_prompt"))
        setting = res.scalar_one_or_none()
        if not setting:
            db.add(BotSettings(key="system_prompt", value=new_prompt, updated_by=user.id))
        else:
            setting.value = new_prompt
            setting.updated_by = user.id
            setting.version += 1
        await db.commit()
        await message.answer("Global prompt updated.")

@router.message(UserStates.setting_time)
async def process_set_time(message: Message, state: FSMContext):
    time_str = (message.text or "").strip()
    import re
    if not re.match(r"^\d{2}:\d{2}$", time_str):
        await message.answer("⚠️ Неверный формат. Пожалуйста, введите время в формате HH:MM (например, 21:00).")
        return
    
    async with async_session() as db:
        user = await _ensure_user(db, message)
        user.notification_time = time_str
        await db.commit()
    
    await message.answer(f"✅ Время напоминаний установлено на <b>{time_str}</b>.", parse_mode=ParseMode.HTML)
    await state.clear()
    # Return to settings menu
    await message.answer("⚙️ <b>Меню настроек</b>", parse_mode=ParseMode.HTML, reply_markup=get_settings_keyboard())

@router.message(UserStates.setting_prompt)
async def process_set_prompt(message: Message, state: FSMContext):
    new_prompt = (message.text or "").strip()
    if len(new_prompt) > 2000:
        await message.answer("⚠️ Слишком длинный текст. Попробуйте короче.")
        return
        
    async with async_session() as db:
        user = await _ensure_user(db, message)
        user.custom_system_prompt = new_prompt
        await db.commit()
    
    await message.answer("✅ <b>Ваш персональный стиль сохранен!</b>", parse_mode=ParseMode.HTML)
    await state.clear()
    await message.answer("⚙️ <b>Меню настроек</b>", parse_mode=ParseMode.HTML, reply_markup=get_settings_keyboard())

@router.message(Command("my_prompt"))
async def cmd_my_prompt(message: Message) -> None:
    # Just redirect to settings menu logic
    async with async_session() as db:
        user = await _ensure_user(db, message)
        current = user.custom_system_prompt or "<i>(стандартный)</i>"
    await message.answer(f"Твой промпт:\n{current}", parse_mode=ParseMode.HTML)

@router.message(Command("set_my_prompt"))
async def cmd_set_my_prompt(message: Message, state: FSMContext) -> None:
    # Check if arguments provided
    args = message.text.replace("/set_my_prompt", "", 1).strip()
    if args:
        # Direct set
        if len(args) > 2000:
            await message.answer("⚠️ Слишком длинный текст.")
            return
        async with async_session() as db:
            user = await _ensure_user(db, message)
            user.custom_system_prompt = args
            await db.commit()
        await message.answer("✅ Стиль обновлен.")
    else:
        # Start FSM
        await state.set_state(UserStates.setting_prompt)
        await message.answer("🎨 Введите новый текст для вашего стиля:")

@router.message(Command("set_time"))
async def cmd_set_time(message: Message, state: FSMContext) -> None:
    args = message.text.replace("/set_time", "", 1).strip()
    if args:
         # Reuse logic? For now strict
        import re
        if not re.match(r"^\d{2}:\d{2}$", args):
            await message.answer("⚠️ Неверный формат. Используйте HH:MM.")
            return
        async with async_session() as db:
            user = await _ensure_user(db, message)
            user.notification_time = args
            await db.commit()
        await message.answer(f"✅ Время установлено: {args}")
    else:
        await state.set_state(UserStates.setting_time)
        await message.answer("⏰ Введите время (HH:MM):")
        await log_event(db, "user_prompt_updated", user.id)
    await message.answer("✅ <b>Твой стиль обновлен!</b>\nТеперь я буду придерживаться этих правил.", parse_mode=ParseMode.HTML)

@router.message(Command("reset_my_prompt"))
async def cmd_reset_my_prompt(message: Message) -> None:
    async with async_session() as db:
        user = await _ensure_user(db, message)
        user.custom_system_prompt = None
        await db.commit()
    await message.answer("✅ Стиль сброшен к стандартному.")

@router.message(Command("export"))
async def cmd_export(message: Message) -> None:
    # Legacy handler, alias to callback logic
    await message.answer("Используй кнопку в меню /start для экспорта.")


# ── Voice / Audio handler ───────────────────────────────────

@router.message(F.content_type.in_({ContentType.VOICE, ContentType.AUDIO}))
async def handle_voice(message: Message) -> None:
    voice = message.voice or message.audio
    if voice is None:
        await message.answer("⚠️ Не удалось получить аудиофайл.")
        return

    duration = voice.duration or 0
    if duration > settings.MAX_VOICE_DURATION_SECONDS:
         # check role inside
         pass 

    processing_msg = await message.answer("🎧 <b>Слушаю и обрабатываю...</b>", parse_mode=ParseMode.HTML)

    async with async_session() as db:
        user = await _ensure_user(db, message)
        
        if user.status in ("blocked", "deleted"):
             await processing_msg.edit_text("⛔ Ваш аккаунт отключен. Обратитесь к администратору @NeuroAlexD.")
             return

        limit_chk = await check_limits(db, user)
        allowed = limit_chk["allowed"]

        if not allowed:
             await processing_msg.edit_text(f'🔒 <b>Лимит исчерпан!</b>\n\n{limit_chk["reason"]}\nЧтобы продолжить, напишите администратору @NeuroAlexD.', parse_mode="HTML")
             return

        if duration > settings.MAX_VOICE_DURATION_SECONDS and user.role != "admin":
             await processing_msg.edit_text(f"⚠️ Слишком длинное голосовое ({duration}с). Лимит {settings.MAX_VOICE_DURATION_SECONDS}с.")
             return

        # Check dedup
        if await _is_duplicate(db, message):
            return

        inp = InputNormalizedDTO(
            tg_user_id=message.from_user.id,
            chat_id=message.chat.id,
            message_id=message.message_id,
            input_type="voice" if message.voice else "audio",
            telegram_file_id=voice.file_id,
            voice_duration=duration,
            locale=message.from_user.language_code or "ru",
            timezone=user.timezone or settings.DEFAULT_TIMEZONE,
            username=message.from_user.username,
        )

        await log_event(db, "message_received", user.id, {
            "input_type": inp.input_type,
            "duration": duration,
        })
        await db.commit()

        try:
            result = await process_message(db, inp, user)
        except Exception as e:
            logger.error(f"Processing error: {e}", exc_info=True)
            await processing_msg.edit_text("⚠️ Ошибка обработки. Попробуйте позже.")
            return

    # Processed logic — split into unlimited Telegram messages (4096 cap each)
    parts = _split_for_telegram(result["text"])

    entry_id = result.get("entry_id")
    kb = None
    if entry_id:
        kb = build_entry_actions_kb(str(entry_id))

    try:
        await deliver_diary_chunks_to_chat(
            parts=parts,
            reply_markup=kb,
            processing_msg=processing_msg,
        )
    except Exception as e:
        logger.error("Deliver diary (voice) failed: %s", e, exc_info=True)
        try:
            await processing_msg.edit_text("⚠️ Произошла непредвиденная ошибка при отправке результата.")
        except Exception:
            pass
        return

    # Anchor for WebApp / admin edit = first bubble (same message_id as "processing")
    if entry_id:
        async with async_session() as db_up:
            from sqlalchemy import update
            await db_up.execute(
                update(JournalEntry)
                .where(JournalEntry.id == entry_id)
                .values(bot_message_id=processing_msg.message_id)
            )
            await db_up.commit()

from aiogram.types import ChatMemberUpdated

@router.chat_member(F.chat.username == "Doronin_Al")
async def on_user_join(event: ChatMemberUpdated):
    # Check if user joined (was not member -> is member/creator/admin)
    old = event.old_chat_member
    new = event.new_chat_member
    
    is_entry = (old.status in ["left", "kicked"] and new.status in ["member", "administrator", "creator"])
    
    if is_entry:
        user_id = new.user.id
        # Send welcome message directly to the user
        try:
             keyboard = get_main_keyboard()
             await event.bot.send_message(
                 chat_id=user_id,
                 text=f"✅ <b>Спасибо за подписку!</b>\nТеперь вы можете пользоваться ботом.\n\n{START_TEXT}",
                 parse_mode=ParseMode.HTML,
                 reply_markup=keyboard
             )
        except Exception as e:
            logger.warning(f"Could not welcome new subscriber {user_id}: {e}")


@router.callback_query(F.data == "check_sub")
async def cb_check_sub(call: CallbackQuery):
    # If we are here, middleware already checked subscription and it passed
    # So we just welcome the user
    await call.message.edit_text("✅ <b>Спасибо за подписку!</b>\nТеперь вы можете пользоваться ботом.", parse_mode=ParseMode.HTML)
    
    # Show main menu
    keyboard = get_main_keyboard()
    await call.message.answer(START_TEXT, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    await call.answer()

@router.message(F.text)
async def handle_text(message: Message) -> None:
    user_text = (message.text or "").strip()
    if not user_text:
        return
    
    # Ignore commands
    if user_text.startswith("/"):
        return

    processing_msg = await message.answer("✍️ <b>Читаю и оформляю...</b>", parse_mode=ParseMode.HTML)

    async with async_session() as db:
        user = await _ensure_user(db, message)
        
        if user.status in ("blocked", "deleted"):
             await processing_msg.edit_text("⛔ Ваш аккаунт отключен. Обратитесь к администратору @NeuroAlexD.")
             return

        limit_chk = await check_limits(db, user)
        allowed = limit_chk["allowed"]
        if not allowed:
             await processing_msg.edit_text(f'🔒 <b>Лимит исчерпан!</b>\n\n{limit_chk["reason"]}\nЧтобы продолжить, напишите администратору @NeuroAlexD.', parse_mode="HTML")
             return

        if await _is_duplicate(db, message):
            return

        inp = InputNormalizedDTO(
            tg_user_id=message.from_user.id,
            chat_id=message.chat.id,
            message_id=message.message_id,
            input_type="text",
            raw_text=user_text,
            locale=message.from_user.language_code or "ru",
            timezone=user.timezone or settings.DEFAULT_TIMEZONE,
            username=message.from_user.username,
        )

        await log_event(db, "message_received", user.id, {"input_type": "text"})
        await db.commit()

        try:
            result = await process_message(db, inp, user)
        except Exception as e:
            logger.error(f"Processing error: {e}", exc_info=True)
            await processing_msg.edit_text("⚠️ Ошибка обработки.")
            return

    parts = _split_for_telegram(result["text"])

    entry_id = result.get("entry_id")
    kb = None
    if entry_id:
        kb = build_entry_actions_kb(str(entry_id))

    try:
        await deliver_diary_chunks_to_chat(
            parts=parts,
            reply_markup=kb,
            processing_msg=processing_msg,
        )
    except Exception as e:
        logger.error("Deliver diary (text) failed: %s", e, exc_info=True)
        try:
            await processing_msg.edit_text("⚠️ Произошла непредвиденная ошибка при отправке результата.")
        except Exception:
            pass
        return

    if entry_id:
        async with async_session() as db_up:
            from sqlalchemy import update
            await db_up.execute(
                update(JournalEntry)
                .where(JournalEntry.id == entry_id)
                .values(bot_message_id=processing_msg.message_id)
            )
            await db_up.commit()



# ── Helpers ──────────────────────────────────────────────────

async def _ensure_user(db, message: Message) -> User:
    """Get or create user in DB."""
    tg_id = message.from_user.id
    result = await db.execute(select(User).where(User.tg_user_id == tg_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            tg_user_id=tg_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            locale=message.from_user.language_code or "ru",
            timezone=settings.DEFAULT_TIMEZONE,
            role="admin" if tg_id in settings.admin_user_ids else "user",
        )
        db.add(user)
        await db.flush()
        logger.info("New user created: tg_id=%s, db_id=%s", tg_id, user.id)

    return user


async def _is_duplicate(db, message: Message) -> bool:
    """Check if this update was already processed (dedup by message_id for simplicity)."""
    # We use a simple approach: check if journal entry with this message_id exists
    result = await db.execute(
        select(TelegramUpdate).where(TelegramUpdate.update_id == message.message_id)
    )
    if result.scalar_one_or_none():
        logger.info("Duplicate message %s — skipping", message.message_id)
        return True

    # Mark as processed
    db.add(TelegramUpdate(update_id=message.message_id, tg_user_id=message.from_user.id))
    await db.flush()
    return False
