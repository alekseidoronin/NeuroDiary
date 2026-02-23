from typing import Any, Awaitable, Callable, Dict
import logging
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from aiogram.enums import ChatMemberStatus
from redis.asyncio import Redis
from sqlalchemy import select

from app.db.engine import async_session
from app.db.models import User
from app.config import settings

logger = logging.getLogger(__name__)

# Channel to check subscription for
REQUIRED_CHANNEL = "@Doronin_Al"
CHANNEL_LINK = "https://t.me/Doronin_Al"
CHANNEL_NAME = "Нейро Алекс чинит бардак!"

# Reuse Redis connection or create new pool?
# Ideally we should share it. But creating separate pool is safe.
redis = Redis.from_url(settings.REDIS_URL, decode_responses=True, encoding="utf-8")

class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user
        
        if not user:
            return await handler(event, data)
            
        # Allow /start always so user can always see the welcome message and potentially resubscribe
        if isinstance(event, Message) and event.text and event.text.startswith("/start"):
            return await handler(event, data)

        # Allow check_sub callback to pass through middleware
        if isinstance(event, CallbackQuery) and event.data == "check_sub":
            return await handler(event, data)
            
        # Skip check for admins
        if user.id in settings.admin_user_ids:
             return await handler(event, data)

        # 1. Check DB Status (Priority: Ban > Subscription)
        try:
            async with async_session() as db:
                result = await db.execute(select(User.status).where(User.tg_user_id == user.id))
                db_status = result.scalar_one_or_none()

                if db_status and str(db_status).lower() in ("blocked", "deleted"):
                    msg = "⛔ Ваш доступ ограничен. Обратитесь к администратору @NeuroAlexD"
                    if isinstance(event, Message):
                        await event.answer(msg)
                    elif isinstance(event, CallbackQuery):
                        await event.answer(msg, show_alert=True)
                    return
        except Exception as e:
            logger.error(f"DB check error in middleware: {e}")
            return

        # 2. Check subscription (with Redis cache)
        cache_key = f"sub_check:{user.id}"
        try:
            is_subscribed = await redis.get(cache_key)
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            is_subscribed = None

        if is_subscribed:
            return await handler(event, data)

        # 3. Check Telegram API
        bot = data["bot"]
        try:
            member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user.id)

            if member.status in [ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER, ChatMemberStatus.RESTRICTED]:
                try:
                    await redis.set(cache_key, "1", ex=300)
                except Exception as e:
                    logger.error(f"Redis set error: {e}")
                return await handler(event, data)
            else:
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub")]
                ])
                text = (
                    "🔒 <b>Доступ только для подписчиков!</b>\n\n"
                    f'Чтобы пользоваться ботом, подпишитесь на канал: <a href="{CHANNEL_LINK}">{CHANNEL_NAME}</a>\n'
                    "После подписки нажмите кнопку ниже.\n\n"
                    "<i>Если возникли проблемы — пишите @NeuroAlexD</i>"
                )
                if isinstance(event, Message):
                    await event.answer(text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=kb)
                elif isinstance(event, CallbackQuery):
                    # If they clicked "check_sub" and still here, it means check failed
                    if event.data == "check_sub":
                        await event.answer("❌ Вы еще не подписались.", show_alert=True)
                    else:
                        await event.answer("Подпишитесь на канал!", show_alert=True)
                return

        except Exception as e:
            logger.error(f"Subscription check failed for {user.id}: {e}")
            text = (
                "🔒 <b>Не удалось проверить подписку на канал.</b>\n\n"
                f'Убедитесь, что вы подписаны на <a href="{CHANNEL_LINK}">{CHANNEL_NAME}</a> и попробуйте снова.\n\n'
                "<i>Если проблема сохраняется — пишите @NeuroAlexD</i>"
            )
            if isinstance(event, Message):
                await event.answer(text, parse_mode="HTML", disable_web_page_preview=True)
            elif isinstance(event, CallbackQuery):
                await event.answer("Ошибка проверки подписки. Попробуйте позже.", show_alert=True)
            return
