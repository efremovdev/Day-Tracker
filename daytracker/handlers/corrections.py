"""Corrections: ``/sterge`` removes the last entry, with confirmation (P4).

"Last entry" is the single most recent entry of *any* type — meal, activity,
water, or weight (DECISIONS.md, 2026-06-18). The confirmation is a reply-keyboard
(Da/Nu), consistent with ``/profil`` and honoring the "no inline callbacks"
decision — the message-only tracked-user gate stays sufficient.

The pending entry's kind + id is held in FSM state, so a tap on "Da" deletes
exactly the entry that was shown, even if something else was logged meanwhile.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .. import repository, strings

router = Router(name="corrections")


class DeleteForm(StatesGroup):
    confirm = State()


def _confirm_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text=strings.STERGE_YES)
    builder.button(text=strings.STERGE_NO)
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


@router.message(Command("sterge"))
async def start_delete(
    message: Message,
    state: FSMContext,
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    async with sessionmaker() as session:
        entry = await repository.get_last_entry(session, telegram_user_id=message.from_user.id)
    if entry is None:
        await message.answer(strings.STERGE_NOTHING)
        return
    await state.set_state(DeleteForm.confirm)
    await state.update_data(kind=entry.kind, entry_id=entry.id)
    await message.answer(strings.format_delete_confirm(entry), reply_markup=_confirm_keyboard())


@router.message(DeleteForm.confirm, F.text == strings.STERGE_YES)
async def confirm_delete(
    message: Message,
    state: FSMContext,
    sessionmaker: async_sessionmaker[AsyncSession],
    tz: ZoneInfo,
) -> None:
    data = await state.get_data()
    await state.clear()
    kind = data.get("kind")
    entry_id = data.get("entry_id")
    if kind is None or entry_id is None:  # defensive; state should always carry both
        await message.answer(strings.STERGE_CANCELLED, reply_markup=ReplyKeyboardRemove())
        return

    today = datetime.now(tz).date()
    async with sessionmaker() as session:
        await repository.delete_entry(session, kind=kind, entry_id=entry_id)
        day = await repository.get_day_totals(
            session, telegram_user_id=message.from_user.id, log_date=today
        )
        profile = await repository.get_profile(session, message.from_user.id)
    await message.answer(
        strings.format_delete_done(kind, day, profile), reply_markup=ReplyKeyboardRemove()
    )


@router.message(DeleteForm.confirm, F.text)
async def cancel_delete(message: Message, state: FSMContext) -> None:
    """Any reply other than "Da" cancels (including the "Nu" button)."""
    await state.clear()
    await message.answer(strings.STERGE_CANCELLED, reply_markup=ReplyKeyboardRemove())
