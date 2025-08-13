from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Iterable

from aiogram import Bot
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.db.models import User, Note
from app.bot.keyboards import triage_keyboard


scheduler = AsyncIOScheduler(timezone=timezone.utc)


async def schedule_user_job(user: User, bot: Bot) -> None:
    job_id = f"triage_{user.id}"
    # Remove existing job
    existing = scheduler.get_job(job_id)
    if existing:
        scheduler.remove_job(job_id)

    try:
        tz = ZoneInfo(user.timezone)
    except Exception:
        tz = ZoneInfo("Europe/Moscow")

    trigger = CronTrigger(hour=21, minute=0, timezone=tz)

    scheduler.add_job(
        triage_user_notes_job,
        trigger=trigger,
        args=[user.id, user.tg_user_id],
        id=job_id,
        replace_existing=True,
        coalesce=True,
        misfire_grace_time=3600,
        max_instances=1,
    )


async def triage_user_notes_job(user_id: int, tg_user_id: int) -> None:
    from app.main import bot  # import here to avoid cycle

    async with async_session_maker() as session:
        # Find today's inbox notes for the user
        user: User | None = await session.get(User, user_id)
        if user is None:
            return

        try:
            tz = ZoneInfo(user.timezone)
        except Exception:
            tz = ZoneInfo("Europe/Moscow")

        now_local = datetime.now(tz)
        start_of_day = datetime(year=now_local.year, month=now_local.month, day=now_local.day, tzinfo=tz)
        # Convert to UTC for DB comparison if DB stores tz-aware UTC. SQLAlchemy with timezone=True keeps tzinfo.

        result = await session.execute(
            select(Note)
            .where(Note.user_id == user_id)
            .where(Note.status == "inbox")
            .where(Note.created_at >= start_of_day)
        )
        notes: list[Note] = list(result.scalars().all())

        if not notes:
            await bot.send_message(chat_id=tg_user_id, text="Сегодня новых заметок нет. До завтра!")
            return

        await bot.send_message(chat_id=tg_user_id, text="21:00 — время распределить заметки за день.")

        for note in notes:
            preview = note.content if len(note.content) <= 350 else note.content[:347] + "..."
            await bot.send_message(
                chat_id=tg_user_id,
                text=f"Заметка #{note.id}:\n{preview}",
                reply_markup=triage_keyboard(note.id),
            )


async def reschedule_all_users(bot: Bot) -> None:
    async with async_session_maker() as session:
        result = await session.execute(select(User))
        users: list[User] = list(result.scalars().all())
        for user in users:
            await schedule_user_job(user, bot)


def start_scheduler() -> None:
    if not scheduler.running:
        scheduler.start()


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)