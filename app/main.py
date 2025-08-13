from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.db.session import create_db_and_tables
from app.bot.handlers import router
from app.scheduler import start_scheduler, shutdown_scheduler, reschedule_all_users


# Global bot reference used by scheduler job
bot: Bot | None = None


async def on_startup(dp: Dispatcher) -> None:
    await create_db_and_tables()
    start_scheduler()
    await reschedule_all_users(bot=dp.bot)


async def on_shutdown(dp: Dispatcher) -> None:
    shutdown_scheduler()


async def main() -> None:
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(level=log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    global bot
    bot = Bot(token=settings.telegram_bot_token, parse_mode="HTML")

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)

    await on_startup(dp)

    try:
        await dp.start_polling(bot)
    finally:
        await on_shutdown(dp)


if __name__ == "__main__":
    asyncio.run(main())