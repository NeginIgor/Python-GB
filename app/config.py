from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


load_dotenv()


@dataclass(slots=True)
class Settings:
    telegram_bot_token: str
    database_url: str
    default_timezone: str = "Europe/Moscow"
    log_level: str = "INFO"

    @staticmethod
    def from_env() -> "Settings":
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            # Default to local SQLite for easier bootstrap
            db_url = "sqlite+aiosqlite:////workspace/notes.db"
        default_tz = os.getenv("DEFAULT_TIMEZONE", "Europe/Moscow")
        log_level = os.getenv("LOG_LEVEL", "INFO")
        return Settings(
            telegram_bot_token=token,
            database_url=db_url,
            default_timezone=default_tz,
            log_level=log_level,
        )


settings = Settings.from_env()