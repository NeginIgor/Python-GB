from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, delete

from app.config import settings
from app.db.session import async_session_maker
from app.db.models import User, Note
from .states import EditNoteStates, SaveNoteStates
from .keyboards import triage_keyboard, category_keyboard, color_keyboard
from app.scheduler import schedule_user_job


router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, command: CommandObject) -> None:
    tg_user = message.from_user
    assert tg_user is not None

    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.tg_user_id == tg_user.id))
        user: User | None = result.scalar_one_or_none()
        if user is None:
            user = User(
                tg_user_id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name,
                timezone=settings.default_timezone,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            await schedule_user_job(user, message.bot)
        else:
            # Update basic fields
            user.username = tg_user.username
            user.first_name = tg_user.first_name
            user.last_name = tg_user.last_name
            await session.commit()

    await message.answer(
        "Привет! Я бот для заметок. Отправляй мне текст — я сохраню его до 21:00.\n"
        "В 21:00 я попрошу распределить заметки: сохранить, редактировать или удалить.\n\n"
        "Текущий часовой пояс: {}. Измени командой /settz <IANA_tz> (например, Europe/Moscow).\n"
        "Посмотреть сохранённые: /notes, посмотреть заметку: /note <id>".format(settings.default_timezone)
    )


@router.message(Command("settz"))
async def cmd_set_timezone(message: Message, command: CommandObject) -> None:
    args = (command.args or "").strip()
    if not args:
        await message.answer("Укажи IANA часовой пояс. Пример: /settz Europe/Moscow")
        return

    try:
        ZoneInfo(args)
    except Exception:
        await message.answer("Некорректный часовой пояс. Пример: Europe/Moscow")
        return

    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.tg_user_id == message.from_user.id))
        user: User | None = result.scalar_one_or_none()
        if user is None:
            await message.answer("Сначала отправь /start")
            return
        user.timezone = args
        await session.commit()
        await schedule_user_job(user, message.bot)

    await message.answer(f"Часовой пояс установлен: {args}. Напомню в 21:00 по твоему времени.")


@router.message(Command("note"))
async def cmd_get_note(message: Message, command: CommandObject) -> None:
    args = (command.args or "").strip()
    if not args or not args.isdigit():
        await message.answer("Использование: /note <id>")
        return
    note_id = int(args)
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.tg_user_id == message.from_user.id))
        user: User | None = result.scalar_one_or_none()
        if user is None:
            await message.answer("Сначала отправь /start")
            return
        note = await session.get(Note, note_id)
        if note is None or note.user_id != user.id or note.status != "saved":
            await message.answer("Заметка не найдена или не сохранена.")
            return
        try:
            tz = ZoneInfo(user.timezone)
        except Exception:
            tz = ZoneInfo("Europe/Moscow")
        ts = note.created_at.astimezone(tz).strftime("%Y-%m-%d %H:%M %Z") if note.created_at.tzinfo else note.created_at.strftime("%Y-%m-%d %H:%M")
        meta_parts = []
        if note.category:
            meta_parts.append(f"Категория: {note.category}")
        if note.color:
            meta_parts.append(f"Цвет: {note.color}")
        meta = (" (" + ", ".join(meta_parts) + ")") if meta_parts else ""
        await message.answer(f"Заметка #{note.id} [{ts}]{meta}:\n{note.content}")


@router.message(Command("notes"))
async def cmd_list_notes(message: Message, command: CommandObject) -> None:
    async with async_session_maker() as session:
        result = await session.execute(
            select(Note).join(User).where(User.tg_user_id == message.from_user.id).where(Note.status == "saved").order_by(Note.created_at.desc()).limit(20)
        )
        notes = list(result.scalars().all())

    if not notes:
        await message.answer("Сохранённых заметок пока нет.")
        return

    # Resolve user's timezone
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.tg_user_id == message.from_user.id))
        user: User | None = result.scalar_one_or_none()
    try:
        tz = ZoneInfo(user.timezone) if user and user.timezone else ZoneInfo("Europe/Moscow")
    except Exception:
        tz = ZoneInfo("Europe/Moscow")

    lines: list[str] = ["Последние сохранённые заметки:"]
    for note in notes:
        ts = note.created_at.astimezone(tz).strftime("%Y-%m-%d %H:%M %Z") if note.created_at.tzinfo else note.created_at.strftime("%Y-%m-%d %H:%M")
        meta_parts = []
        if note.category:
            meta_parts.append(f"Категория: {note.category}")
        if note.color:
            meta_parts.append(f"Цвет: {note.color}")
        meta = (" (" + ", ".join(meta_parts) + ")") if meta_parts else ""
        content = note.content if len(note.content) <= 200 else note.content[:197] + "..."
        lines.append(f"• #{note.id} [{ts}]{meta}: {content}")

    await message.answer("\n".join(lines))


@router.message(F.text & ~F.via_bot & ~F.text.startswith("/"))
async def handle_text_note(message: Message) -> None:
    tg_user = message.from_user
    assert tg_user is not None

    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.tg_user_id == tg_user.id))
        user: User | None = result.scalar_one_or_none()
        if user is None:
            await message.answer("Сначала отправь /start")
            return

        note = Note(user_id=user.id, content=message.text or "", status="inbox")
        session.add(note)
        await session.commit()

    await message.answer("Заметка добавлена в сегодняшний список. Я напомню в 21:00.")


# Callbacks: triage actions
@router.callback_query(F.data.startswith("triage:"))
async def cb_triage_action(callback: CallbackQuery, state: FSMContext) -> None:
    data = callback.data.split(":")  # triage:action:note_id
    if len(data) != 3:
        await callback.answer()
        return
    _, action, note_id_str = data
    try:
        note_id = int(note_id_str)
    except ValueError:
        await callback.answer()
        return

    async with async_session_maker() as session:
        note = await session.get(Note, note_id)
        if not note:
            await callback.answer("Заметка не найдена", show_alert=True)
            return

    if action == "save":
        await state.update_data(note_id=note_id)
        await state.set_state(SaveNoteStates.picking_category)
        await callback.message.answer("Выбери категорию:", reply_markup=category_keyboard(note_id))
        await callback.answer()
    elif action == "edit":
        await state.update_data(note_id=note_id)
        await state.set_state(EditNoteStates.waiting_for_new_text)
        await callback.message.answer("Отправь новый текст заметки:")
        await callback.answer()
    elif action == "delete":
        async with async_session_maker() as session:
            await session.execute(delete(Note).where(Note.id == note_id))
            await session.commit()
        await callback.message.edit_text("Заметка удалена.")
        await callback.answer("Удалено")
    else:
        await callback.answer()


@router.callback_query(F.data.startswith("save:category:"))
async def cb_pick_category(callback: CallbackQuery, state: FSMContext) -> None:
    # save:category:<note_id>:<category>
    parts = callback.data.split(":", maxsplit=3)
    if len(parts) != 4:
        await callback.answer()
        return
    _, _, note_id_str, category = parts
    try:
        note_id = int(note_id_str)
    except ValueError:
        await callback.answer()
        return

    await state.update_data(note_id=note_id, category=category)
    await state.set_state(SaveNoteStates.picking_color)
    await callback.message.edit_text(f"Категория: {category}. Теперь выбери цвет (или 'Без цвета'):", reply_markup=color_keyboard(note_id))
    await callback.answer()


@router.callback_query(F.data.startswith("save:color:"))
async def cb_pick_color(callback: CallbackQuery, state: FSMContext) -> None:
    # save:color:<note_id>:<color>
    parts = callback.data.split(":")
    if len(parts) != 4:
        await callback.answer()
        return
    _, _, note_id_str, color = parts
    try:
        note_id = int(note_id_str)
    except ValueError:
        await callback.answer()
        return

    data = await state.get_data()
    category = data.get("category")
    if not category:
        await callback.answer("Сначала выбери категорию", show_alert=True)
        return

    async with async_session_maker() as session:
        note = await session.get(Note, note_id)
        if not note:
            await callback.answer("Заметка не найдена", show_alert=True)
            return
        note.category = category
        note.color = color
        note.status = "saved"
        await session.commit()

    await callback.message.edit_text(f"Сохранено. Категория: {category}, Цвет: {color}")
    await state.clear()
    await callback.answer("Сохранено")


@router.callback_query(F.data.startswith("save:color_skip:"))
async def cb_skip_color(callback: CallbackQuery, state: FSMContext) -> None:
    # save:color_skip:<note_id>
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer()
        return
    _, _, note_id_str = parts
    try:
        note_id = int(note_id_str)
    except ValueError:
        await callback.answer()
        return

    data = await state.get_data()
    category = data.get("category")
    if not category:
        await callback.answer("Сначала выбери категорию", show_alert=True)
        return

    async with async_session_maker() as session:
        note = await session.get(Note, note_id)
        if not note:
            await callback.answer("Заметка не найдена", show_alert=True)
            return
        note.category = category
        note.color = None
        note.status = "saved"
        await session.commit()

    await callback.message.edit_text(f"Сохранено. Категория: {category}.")
    await state.clear()
    await callback.answer("Сохранено")


@router.callback_query(F.data.startswith("save:cancel:"))
async def cb_save_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Действие отменено.")
    await callback.answer()


@router.message(EditNoteStates.waiting_for_new_text, F.text)
async def handle_edit_text(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    note_id = data.get("note_id")
    if not note_id:
        await state.clear()
        await message.answer("Состояние потеряно. Повтори действие.")
        return

    new_text = message.text or ""
    async with async_session_maker() as session:
        note = await session.get(Note, int(note_id))
        if not note:
            await message.answer("Заметка не найдена")
            await state.clear()
            return
        note.content = new_text
        await session.commit()

    # After editing, go to save flow (category -> color)
    await state.set_state(SaveNoteStates.picking_category)
    await message.answer("Текст обновлён. Теперь выбери категорию:", reply_markup=category_keyboard(int(note_id)))