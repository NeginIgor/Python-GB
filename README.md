# Telegram Notes Bot

Async Telegram bot that collects notes during the day and at 21:00 asks you to classify each: save, edit, or delete. Saved notes can be retrieved later with timestamps and optional category/color.

## Features
- Collect notes from user messages anytime (inbox)
- Daily 21:00 reminder per user timezone to triage notes
- Actions per note: Save (choose category and optional color), Edit, Delete
- List saved notes with timestamps
- Per-user timezone with daily scheduled job

## Tech
- aiogram v3 (async)
- SQLAlchemy 2.0 (async ORM) + SQLite (default via aiosqlite) or PostgreSQL (asyncpg)
- APScheduler (AsyncIOScheduler) for per-user daily jobs
- Python 3.11+

## Quickstart
1. Create `.env` from example:
```
cp .env.example .env
```

2. Fill `.env`:
```
TELEGRAM_BOT_TOKEN=123456:ABCDEF...
# Optional: Postgres URL. If omitted, uses SQLite at /workspace/notes.db
# DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/notes
DEFAULT_TIMEZONE=Europe/Moscow
```

3. Install dependencies:
```
pip3 install -r requirements.txt
```

4. Run the bot:
```
python3 -m app.main
```

## Commands
- /start — register and set timezone
- /settz <IANA_tz> — set timezone, e.g. `/settz Europe/Moscow`
- /notes — list your saved notes (recent)
- /note <id> — show a specific saved note with timestamp and metadata
- Send any text — creates a note in your inbox for today

## Notes
- Each user gets a daily job at 21:00 in their timezone. On start or timezone change, the job is (re)scheduled. On restart, jobs are rehydrated from the database.
- Timestamps in lists and single note view are shown in your configured timezone.
- Default categories: Work, Personal, Other. You can extend later.
- To switch to PostgreSQL, set `DATABASE_URL` env to `postgresql+asyncpg://...` and restart.