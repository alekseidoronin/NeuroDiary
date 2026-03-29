# Резервное копирование PostgreSQL

Скрипт [`pg_backup.sh`](pg_backup.sh) делает сжатый логический дамп (`pg_dump -Fc`) из контейнера `postgres`.

## Требования

- Docker на том же хосте, где крутится `docker compose`.
- Имя контейнера по умолчанию: `diary-bot-postgres-1` (как у `docker compose` с проектом `diary-bot`). Если другое — задайте `PG_CONTAINER`.

## Однократный запуск

```bash
cd /path/to/diary-bot
chmod +x scripts/backup/pg_backup.sh
BACKUP_DIR=/var/backups/diary-bot ./scripts/backup/pg_backup.sh
```

## Восстановление (на новом хосте / после сбоя)

```bash
# в контейнере postgres, файл dump на хосте смонтирован или скопирован внутрь
pg_restore -U diary -d diarybot --clean --if-exists /path/to/diarybot_YYYYMMDD.dump
```

Храните дампы так же охраняемо, как саму БД (в них есть данные пользователей и зашифрованные настройки).
