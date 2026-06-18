"""The daily summary (P5).

- ``/sumar`` — on-demand daily summary (replies to the message).

The same data + formatter back the scheduled 21:00 auto-summary (see
:mod:`daytracker.scheduler`), so the two outputs match (PLAN.md P5 acceptance).
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .. import repository, strings

router = Router(name="summary")


@router.message(Command("sumar"))
async def sumar_command(
    message: Message,
    sessionmaker: async_sessionmaker[AsyncSession],
    tz: ZoneInfo,
) -> None:
    today = datetime.now(tz).date()
    async with sessionmaker() as session:
        summary = await repository.get_day_summary(
            session, telegram_user_id=message.from_user.id, log_date=today
        )
    await message.answer(strings.format_summary(summary))
