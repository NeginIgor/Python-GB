from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def triage_keyboard(note_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Сохранить", callback_data=f"triage:save:{note_id}"),
                InlineKeyboardButton(text="Редактировать", callback_data=f"triage:edit:{note_id}"),
                InlineKeyboardButton(text="Удалить", callback_data=f"triage:delete:{note_id}"),
            ]
        ]
    )


def category_keyboard(note_id: int) -> InlineKeyboardMarkup:
    categories = [
        ("Работа", "Work"),
        ("Личное", "Personal"),
        ("Другое", "Other"),
    ]
    row = [InlineKeyboardButton(text=title, callback_data=f"save:category:{note_id}:{value}") for title, value in categories]
    return InlineKeyboardMarkup(inline_keyboard=[row, [InlineKeyboardButton(text="Отмена", callback_data=f"save:cancel:{note_id}")]])


def color_keyboard(note_id: int) -> InlineKeyboardMarkup:
    colors = [
        ("Красный", "red"),
        ("Зеленый", "green"),
        ("Синий", "blue"),
        ("Желтый", "yellow"),
        ("Фиолетовый", "purple"),
        ("Серый", "gray"),
    ]
    rows = [
        [InlineKeyboardButton(text=title, callback_data=f"save:color:{note_id}:{value}") for title, value in colors[:3]],
        [InlineKeyboardButton(text=title, callback_data=f"save:color:{note_id}:{value}") for title, value in colors[3:]],
        [InlineKeyboardButton(text="Без цвета", callback_data=f"save:color_skip:{note_id}"), InlineKeyboardButton(text="Отмена", callback_data=f"save:cancel:{note_id}")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)