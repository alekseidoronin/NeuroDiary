# 📓 DiaryCode Bot v2

Telegram-бот для ведения структурированного дневника с админкой (Mini App).

**Стек:** Python (FastAPI + aiogram) · PostgreSQL · AssemblyAI (STT) · Gemini/OpenAI (LLM) · React (Mini App)

---

## 🏗 Архитектура

```
Telegram User
    │
    ▼
┌─────────────────────────────────────────┐
│ Webhook (FastAPI)                       │
│   ├── /webhook/telegram  ← updates     │
│   ├── /admin/*           ← Mini App    │
│   └── /health                          │
└─────────┬───────────────────────────────┘
          │
    ┌─────▼──────┐
    │  Pipeline   │
    │             │
    │  1. Dedup   │
    │  2. Limits  │
    │  3. STT     │──→ AssemblyAI
    │  4. LLM     │──→ Gemini / OpenAI
    │  5. Validate│
    │  6. Repair  │──→ LLM (if needed)
    │  7. Save    │
    └─────┬───────┘
          │
    ┌─────▼──────┐
    │ PostgreSQL  │
    │  - users    │
    │  - entries  │
    │  - events   │
    │  - billing  │
    └─────────────┘
```

## 📁 Структура проекта

```
diary-bot/
├── app/                        # Backend
│   ├── main.py                 # FastAPI entry point
│   ├── config.py               # Settings (pydantic-settings)
│   ├── api/
│   │   ├── webhook.py          # Telegram handlers
│   │   ├── admin.py            # Admin REST API
│   │   └── auth.py             # Mini App auth (HMAC)
│   ├── db/
│   │   ├── engine.py           # SQLAlchemy async engine
│   │   └── models.py           # ORM models (10 tables)
│   ├── dto/
│   │   ├── telegram.py         # InputNormalizedDTO
│   │   ├── stt.py              # STTRequest/ResultDTO
│   │   ├── llm.py              # LLMRequest/ResultDTO
│   │   └── validation.py       # FormatValidationDTO
│   └── services/
│       ├── pipeline.py         # Main processing chain
│       ├── prompts.py          # 3 prompts (system/user/repair)
│       ├── validator.py        # Format checker (6 checks)
│       ├── billing.py          # Limits & usage tracking
│       ├── events.py           # Event logger
│       ├── stt/
│       │   ├── base.py         # Abstract STT provider
│       │   └── assemblyai_provider.py
│       └── llm/
│           ├── base.py         # Abstract LLM provider
│           ├── gemini_provider.py
│           └── openai_provider.py
├── admin-app/                  # Telegram Mini App (React)
│   ├── src/
│   │   ├── App.jsx             # 5-tab admin UI
│   │   ├── api.js              # API client
│   │   ├── main.jsx            # Entry point
│   │   └── index.css           # Design system
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── docker-compose.yml          # Postgres + Redis
├── requirements.txt
├── .env.example
└── README.md
```

## 🚀 Быстрый старт

### 1. Запустить Postgres + Redis

```bash
docker-compose up -d
```

### 2. Установить Python-зависимости

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Настроить .env

```bash
cp .env.example .env
# Заполнить: TELEGRAM_BOT_TOKEN, ASSEMBLYAI_API_KEY, GEMINI_API_KEY
```

### 4. Запустить бота (dev — polling)

```bash
python -m app.main polling
```

### 5. Запустить Mini App (dev)

```bash
cd admin-app
npm install
npm run dev
```

## 📋 Команды бота

| Команда   | Описание                     |
|-----------|------------------------------|
| `/start`  | Приветствие и инструкция     |
| `/prompt` | Текущий системный промт      |
| `/export` | Последние 5 записей          |

## 🎯 Пайплайн обработки

1. **Telegram Ingest** — webhook получает update, 200 OK
2. **Dedup** — проверяет `telegram_updates` таблицу
3. **Limits** — проверяет подписку и дневной usage
4. **STT** (если voice) — AssemblyAI transcribe
5. **LLM** — Gemini/OpenAI с 3 промтами
6. **Validate** — 6 проверок формата
7. **Repair** (если невалидно) — 1 попытка через LLM
8. **Save** — `journal_entries` + `events` + `usage_daily`
9. **Send** — ответ в Telegram

## 🗄 База данных (PostgreSQL)

| Таблица             | Назначение                          |
|---------------------|-------------------------------------|
| `users`             | Пользователи + роли                 |
| `telegram_updates`  | Дедупликация update_id               |
| `journal_entries`   | Записи дневника (raw + final)        |
| `provider_jobs`     | Наблюдаемость STT/LLM               |
| `events`            | Event log (все действия)             |
| `plans`             | Тарифы                               |
| `subscriptions`     | Подписки пользователей               |
| `payments`          | Платежи                              |
| `usage_daily`       | Дневные счётчики (entries, stt, tokens) |
| `bot_settings`      | Настройки бота (ключи зашифрованы)   |

## 🖥 Админка (Mini App)

5 экранов:
- **Дашборд** — DAU/WAU, записи/день, voice vs text, ошибки
- **Юзеры** — список, поиск, карточка с usage
- **Записи** — просмотр raw/transcript/final
- **Логи** — поток событий, фильтры
- **Настройки** — провайдер, ключи, промты

Открывается через: `https://t.me/<bot>?startapp=admin`

## 🔐 Безопасность

- Telegram init data HMAC-SHA256 валидация
- API ключи — encrypted в БД (Fernet)
- Ключи никогда не пишутся в логи
- Admin-only доступ по `role` из таблицы `users`
