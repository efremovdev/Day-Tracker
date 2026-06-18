"""Scheduled jobs (P5/P6): the 21:00 Europe/Bucharest evening summaries.

APScheduler runs in the bot's own asyncio loop (``AsyncIOScheduler``). One cron job
fires at 21:00 daily and calls :func:`send_evening_summaries`, which always sends the
daily summary and, **on Sundays, the weekly report right after** (sequential ``await``
so the daily lands first — DECISIONS.md, 2026-06-18). Both use the same data +
formatters as ``/sumar`` / ``/saptamana`` (see :mod:`daytracker.handlers.summary`), so
scheduled and on-demand outputs match (PLAN.md P5/P6 acceptance). They're unsolicited,
so they're posted to the chat the user last wrote in (remembered via
:class:`daytracker.middlewares.ChatRecorderMiddleware`).

The job list isn't persisted: a run missed because the process was *down* at 21:00 is
not replayed on restart — restart safety is a P7 concern. ``misfire_grace_time`` only
covers a brief delay while the running loop is busy.
"""

from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from . import repository, strings

logger = logging.getLogger(__name__)

# Locked by DECISIONS.md (2026-06-17): summaries auto-sent at 21:00; the weekly report
# rides the same 21:00 slot on Sundays (DECISIONS.md, 2026-06-18).
DAILY_SUMMARY_HOUR = 21
DAILY_SUMMARY_MINUTE = 0
SUNDAY = 6  # date.weekday(): Monday=0 … Sunday=6


async def send_daily_summary(
    *,
    bot: Bot,
    sessionmaker: async_sessionmaker[AsyncSession],
    tz: ZoneInfo,
    tracked_user_id: int,
) -> None:
    """Build the day's summary and post it to the user's last-used chat."""
    today = datetime.now(tz).date()
    async with sessionmaker() as session:
        chat_id = await repository.get_chat_id(session, telegram_user_id=tracked_user_id)
        if chat_id is None:
            logger.info("Daily summary skipped: no chat recorded yet (user hasn't written).")
            return
        summary = await repository.get_day_summary(
            session, telegram_user_id=tracked_user_id, log_date=today
        )
    try:
        await bot.send_message(chat_id, strings.format_summary(summary))
        logger.info("Daily summary sent to chat %s for %s.", chat_id, today)
    except Exception:  # a send failure must not crash the scheduler
        logger.exception("Failed to send the daily summary.")


async def send_weekly_report(
    *,
    bot: Bot,
    sessionmaker: async_sessionmaker[AsyncSession],
    tz: ZoneInfo,
    tracked_user_id: int,
) -> None:
    """Build the week's report and post it to the user's last-used chat."""
    today = datetime.now(tz).date()
    async with sessionmaker() as session:
        chat_id = await repository.get_chat_id(session, telegram_user_id=tracked_user_id)
        if chat_id is None:
            logger.info("Weekly report skipped: no chat recorded yet (user hasn't written).")
            return
        week = await repository.get_week_summary(
            session, telegram_user_id=tracked_user_id, end_date=today
        )
    try:
        await bot.send_message(chat_id, strings.format_weekly_report(week))
        logger.info("Weekly report sent to chat %s for week ending %s.", chat_id, today)
    except Exception:  # a send failure must not crash the scheduler
        logger.exception("Failed to send the weekly report.")


async def send_evening_summaries(
    *,
    bot: Bot,
    sessionmaker: async_sessionmaker[AsyncSession],
    tz: ZoneInfo,
    tracked_user_id: int,
) -> None:
    """The 21:00 job: the daily summary every day, plus the weekly report on Sundays.

    Sequential ``await`` guarantees the daily lands before the weekly. Each send wraps
    its own errors, so a daily failure still lets the weekly go out.
    """
    await send_daily_summary(
        bot=bot, sessionmaker=sessionmaker, tz=tz, tracked_user_id=tracked_user_id
    )
    if datetime.now(tz).weekday() == SUNDAY:
        await send_weekly_report(
            bot=bot, sessionmaker=sessionmaker, tz=tz, tracked_user_id=tracked_user_id
        )


def create_scheduler(
    *,
    bot: Bot,
    sessionmaker: async_sessionmaker[AsyncSession],
    tz: ZoneInfo,
    tracked_user_id: int,
) -> AsyncIOScheduler:
    """Build (not start) the scheduler with the 21:00 evening-summaries job."""
    scheduler = AsyncIOScheduler(timezone=tz)
    scheduler.add_job(
        send_evening_summaries,
        trigger=CronTrigger(hour=DAILY_SUMMARY_HOUR, minute=DAILY_SUMMARY_MINUTE, timezone=tz),
        kwargs={
            "bot": bot,
            "sessionmaker": sessionmaker,
            "tz": tz,
            "tracked_user_id": tracked_user_id,
        },
        id="evening_summaries",
        coalesce=True,
        misfire_grace_time=3600,
        replace_existing=True,
    )
    return scheduler
