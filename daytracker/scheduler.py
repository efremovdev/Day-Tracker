"""Scheduled jobs (P5): the automatic daily summary at 21:00 Europe/Bucharest.

APScheduler runs in the bot's own asyncio loop (``AsyncIOScheduler``). The job uses
the same data + formatter as ``/sumar`` (see :mod:`daytracker.handlers.summary`), so
the scheduled and on-demand summaries match (PLAN.md P5 acceptance). The summary is
unsolicited, so it's posted to the chat the user last wrote in (remembered via
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

# Locked by DECISIONS.md (2026-06-17): daily summary auto-sent at 21:00.
DAILY_SUMMARY_HOUR = 21
DAILY_SUMMARY_MINUTE = 0


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


def create_scheduler(
    *,
    bot: Bot,
    sessionmaker: async_sessionmaker[AsyncSession],
    tz: ZoneInfo,
    tracked_user_id: int,
) -> AsyncIOScheduler:
    """Build (not start) the scheduler with the 21:00 daily-summary job."""
    scheduler = AsyncIOScheduler(timezone=tz)
    scheduler.add_job(
        send_daily_summary,
        trigger=CronTrigger(hour=DAILY_SUMMARY_HOUR, minute=DAILY_SUMMARY_MINUTE, timezone=tz),
        kwargs={
            "bot": bot,
            "sessionmaker": sessionmaker,
            "tz": tz,
            "tracked_user_id": tracked_user_id,
        },
        id="daily_summary",
        coalesce=True,
        misfire_grace_time=3600,
        replace_existing=True,
    )
    return scheduler
