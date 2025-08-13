from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class EditNoteStates(StatesGroup):
    waiting_for_new_text = State()


class SaveNoteStates(StatesGroup):
    picking_category = State()
    picking_color = State()