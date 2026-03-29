# Инструкция: Настройка озвучки ответов в Telegram-боте

## Что нужно

1. **Сервер/VPS** с Linux (Ubuntu/Debian)
2. **Python 3.11+**
3. **Telegram Bot Token** (получить у @BotFather)
4. **Библиотека gTTS** (Google Text-to-Speech)

## Шаг 1: Установка зависимостей

```bash
# Обновляем систему
sudo apt update && sudo apt upgrade -y

# Устанавливаем Python и pip
sudo apt install python3 python3-pip python3-venv -y

# Устанавливаем gTTS
pip3 install gtts --user --break-system-packages
```

## Шаг 2: Создание скрипта озвучки

Создай файл `speak.py`:

```python
#!/usr/bin/env python3
"""Telegram Voice Sender - отправка голосовых сообщений"""

import os
import sys
import hashlib
from gtts import gTTS
from pathlib import Path

# Настройки
CACHE_DIR = Path("/tmp/tts_cache")
CACHE_DIR.mkdir(exist_ok=True)
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

def generate_voice(text: str, lang: str = "ru") -> str:
    """Генерирует MP3 из текста, использует кэш"""
    
    # Лимит символов для Telegram
    if len(text) > 4000:
        text = text[:4000] + "..."
    
    # Кэширование
    cache_key = hashlib.md5(f"{text}:{lang}".encode()).hexdigest()
    audio_path = CACHE_DIR / f"{cache_key}.mp3"
    
    if audio_path.exists():
        return str(audio_path)
    
    # Генерация
    tts = gTTS(text=text, lang=lang, slow=False)
    tts.save(str(audio_path))
    
    return str(audio_path)

def send_voice(text: str, chat_id: str = None) -> bool:
    """Отправляет голосовое в Telegram"""
    
    if not BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not set")
        return False
    
    chat_id = chat_id or CHAT_ID
    if not chat_id:
        print("Error: CHAT_ID not set")
        return False
    
    # Генерируем аудио
    audio_file = generate_voice(text)
    
    # Отправляем через curl
    import subprocess
    
    cmd = [
        "curl", "-s", "-X", "POST",
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice",
        "-F", f"chat_id={chat_id}",
        "-F", f"voice=@{audio_file}",
        "-F", "caption=🔊 Голосовой ответ"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if '"ok":true' in result.stdout:
        print(f"✅ Voice sent: {len(text)} chars")
        return True
    else:
        print(f"❌ Error: {result.stdout}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 speak.py 'Текст для озвучки'")
        sys.exit(1)
    
    text = sys.argv[1]
    send_voice(text)
```

## Шаг 3: Настройка переменных окружения

Создай файл `.env`:

```bash
TELEGRAM_BOT_TOKEN=твой_токен_от_BotFather
TELEGRAM_CHAT_ID=id_чата_куда_отправлять
```

Загружай перед запуском:
```bash
export $(grep -v '^#' .env | xargs)
```

## Шаг 4: Интеграция с ботом

### Вариант A: Через команду

Добавь в обработчик сообщений:

```python
# Если сообщение содержит триггерные слова
VOICE_TRIGGERS = ['озвучь', 'голос', 'скажи', 'прочитай', 'tts']

if any(trigger in user_message.lower() for trigger in VOICE_TRIGGERS):
    # Запускаем озвучку
    import subprocess
    subprocess.run([
        'python3', '/path/to/speak.py', 
        bot_response_text
    ])
```

### Вариант B: Автоматически после каждого ответа

```python
def send_response(chat_id, text):
    # Отправляем текст
    bot.send_message(chat_id, text)
    
    # Отправляем голос
    import subprocess
    subprocess.run([
        'python3', '/path/to/speak.py', text
    ])
```

### Вариант C: По кнопке

Добавь inline-кнопку:

```python
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_voice_button():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(
        "🔊 Прослушать", 
        callback_data="tts_last"
    ))
    return markup

# При отправке сообщения
bot.send_message(
    chat_id, 
    response_text,
    reply_markup=get_voice_button()
)

# Обработчик кнопки
@bot.callback_query_handler(func=lambda call: call.data == "tts_last")
def handle_voice_button(call):
    # Получаем текст последнего сообщения
    last_text = get_last_bot_message(call.message.chat.id)
    
    # Отправляем голос
    import subprocess
    subprocess.run([
        'python3', '/path/to/speak.py', last_text
    ])
```

## Шаг 5: Тестирование

```bash
# Загружаем токен
export $(grep -v '^#' .env | xargs)

# Тестируем
python3 speak.py "Привет! Это тестовое сообщение."
```

## Команды для пользователя

- `озвучь` — озвучить последний ответ
- `голос` — то же самое
- `скажи` — то же самое
- `tts` — то же самое

## Примечания

1. **API-ключ для TTS не нужен** — `gTTS` работает без отдельной авторизации.
2. **Нужен интернет** — синтез выполняется через внешний сервис Google TTS.
3. **Кэширование** — повторные фразы берутся из кэша мгновенно.
4. **Лимиты** — максимум 4000 символов на одно сообщение.
5. **Язык** — по умолчанию русский, можно менять на `en`, `de` и др.

## Устранение неполадок

**Ошибка: No module named 'gtts'**
```bash
pip3 install gtts --user --break-system-packages
```

**Ошибка: TELEGRAM_BOT_TOKEN not set**
```bash
# Проверь что файл .env существует и загружен
source .env
```

**Голос не отправляется**
```bash
# Проверь токен
curl "https://api.telegram.org/bot<ТОКЕН>/getMe"
```

---

*Создано для Нейро Алекса*
*Дата: 24.03.2025*
