
import asyncio
from aiogram import Bot
from aiogram.types import MenuButtonWebApp, WebAppInfo, MenuButtonCommands
from app.config import settings

# Настройки
ADMIN_TG_ID = 632600126
WEB_APP_URL = "https://diary.144.217.12.20.nip.io/admin-app"

async def fix_menu():
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    
    print("Подключаюсь к Telegram API...")

    # 1. Устанавливаем ГЛОБАЛЬНУЮ кнопку (для всех) как "Команды"
    # Это перекроет настройку из BotFather (где стоит Web App)
    await bot.set_chat_menu_button(
        chat_id=None, 
        menu_button=MenuButtonCommands()
    )
    print("✅ Глобальная кнопка изменена на 'Команды' (обычные юзеры увидят меню).")

    # 2. Восстанавливаем кнопку Админки лично для вас
    await bot.set_chat_menu_button(
        chat_id=ADMIN_TG_ID,
        menu_button=MenuButtonWebApp(
            text="Админка", 
            web_app=WebAppInfo(url=WEB_APP_URL)
        )
    )
    print(f"✅ Персональная кнопка 'Админка' установлена для {ADMIN_TG_ID}.")
    
    # 3. На всякий случай сбрасываем для Neo (784200345) чтобы он увидел глобальную
    neo_id = 784200345
    try:
        await bot.set_chat_menu_button(chat_id=neo_id, menu_button=None) # None = default
        print(f"✅ Сброшена кнопка для {neo_id} (увидит глобальную).")
    except:
        pass

    await bot.session.close()

if __name__ == "__main__":
    asyncio.run(fix_menu())
