"""The daily summary (P5) and weekly report (P6).

- ``/sumar`` — on-demand daily summary (replies to the message).
- ``/saptamana`` — on-demand weekly report (replies to the message).

The same data + formatters back the scheduled 21:00 auto-summary and the Sunday-night
weekly report (see :mod:`daytracker.scheduler`), so on-demand and scheduled outputs
match (PLAN.md P5/P6 acceptance).
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


@router.message(Command("saptamana"))
async def saptamana_command(
    message: Message,
    sessionmaker: async_sessionmaker[AsyncSession],
    tz: ZoneInfo,
) -> None:
    today = datetime.now(tz).date()
    async with sessionmaker() as session:
        week = await repository.get_week_summary(
            session, telegram_user_id=message.from_user.id, end_date=today
        )
    await message.answer(strings.format_weekly_report(week))
