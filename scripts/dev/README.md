# Dev / one-off scripts

Запускайте **из корня репозитория**, чтобы работали импорты `app.*`:

```bash
cd /path/to/diary-bot
export PYTHONPATH=.
python scripts/dev/check_errors.py
```

## Содержимое

| Скрипт | Назначение |
|--------|------------|
| `import_diary.py` | Импорт архива в БД; `--text-file`, `--user-id` или `--tg-user-id` |
| `export_diary.py` | HTML-экспорт; обязательно `--user-id` *или* `--tg-user-id`; опционально `-o путь.html` |
| `send_history.py` | Все записи в Telegram; `--user-id` *или* `--tg-user-id`; `--delay` между сообщениями |
| `check_*.py`, `diag_settings.py`, `test_*.py`, `list_gemini_models.py` | Диагностика и тесты |
| `fix_db_model.py`, `update_model.py`, `set_private_menu.py`, `check_db_*.py` | Разовые операции с БД/ботом |

Файл `data/import_payload.txt` (личные данные) в git не входит — см. `.gitignore`.
