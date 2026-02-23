
import asyncio
from aiogram import Bot
from aiogram.types import MenuButtonWebApp, WebAppInfo, MenuButtonDefault
from app.config import settings

# Настройки
ADMIN_TG_ID = 632600126  # Ваш ID (Алексей)
WEB_APP_URL = "https://diary.144.217.12.20.nip.io/admin-app"

async def set_menu():
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    
    # 1. Сбрасываем глобальную кнопку (чтобы у обычных юзеров её не было)
    # Примечание: Это удалит кнопку из BotFather'а "Menu Button"
    await bot.set_chat_menu_button(chat_id=None, menu_button=MenuButtonDefault())
    print("Глобальная кнопка сброшена (обычные пользователи её не увидят).")

    # 2. Устанавливаем кнопку ТОЛЬКО для админа
    await bot.set_chat_menu_button(
        chat_id=ADMIN_TG_ID,
        menu_button=MenuButtonWebApp(
            text="Админка", 
            web_app=WebAppInfo(url=WEB_APP_URL)
        )
    )
    print(f"Кнопка 'Админка' установлена лично для пользователя {ADMIN_TG_ID}.")

    await bot.session.close()

if __name__ == "__main__":
    asyncio.run(set_menu())
