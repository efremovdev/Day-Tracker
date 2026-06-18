"""Meal logging (`/masa`).

Works two ways (DECISIONS.md, 2026-06-17):
- as a text command: ``/masa 100g piept de pui, 40g orez``
- as a photo caption starting with ``/masa`` — the image is never analyzed, only
  the caption text is read.

aiogram's ``Command`` filter only matches ``message.text``, so the photo-caption
path needs its own handler that parses the command out of ``message.caption``.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .. import repository, strings
from ..estimator import MacroEstimator, MacroEstimatorError

logger = logging.getLogger(__name__)

router = Router(name="meals")

# Cap the free-text meal description so an accidental wall of text can't be stored or
# shipped to the LLM (P7 input validation). Generous — normal meals are far shorter.
MAX_MEAL_TEXT = 1000

# Matches a "/masa" caption (optionally "/masa@BotName") and captures the rest.
_MASA_CAPTION_RE = re.compile(r"^/masa(?:@\w+)?(?:\s+(?P<args>.*))?$", re.IGNORECASE | re.DOTALL)


@router.message(Command("masa"))
async def masa_command(
    message: Message,
    command: CommandObject,
    sessionmaker: async_sessionmaker[AsyncSession],
    estimator: MacroEstimator,
    tz: ZoneInfo,
) -> None:
    await _log_meal(message, command.args, sessionmaker=sessionmaker, estimator=estimator, tz=tz)


@router.message(F.photo, F.caption.regexp(r"(?i)^/masa(@\w+)?(\s|$)"))
async def masa_caption(
    message: Message,
    sessionmaker: async_sessionmaker[AsyncSession],
    estimator: MacroEstimator,
    tz: ZoneInfo,
) -> None:
    match = _MASA_CAPTION_RE.match((message.caption or "").strip())
    args = match.group("args") if match else None
    await _log_meal(message, args, sessionmaker=sessionmaker, estimator=estimator, tz=tz)


async def _log_meal(
    message: Message,
    food_text: str | None,
    *,
    sessionmaker: async_sessionmaker[AsyncSession],
    estimator: MacroEstimator,
    tz: ZoneInfo,
) -> None:
    text = (food_text or "").strip()
    if not text:
        await message.answer(strings.MASA_EMPTY)
        return
    if len(text) > MAX_MEAL_TEXT:
        await message.answer(strings.MASA_TOO_LONG)
        return

    # Estimating calls the LLM and can take a couple of seconds — show "typing".
    # Best-effort: a hiccup here must not abort logging the meal (P7).
    try:
        await message.bot.send_chat_action(message.chat.id, "typing")
    except Exception:
        logger.warning("send_chat_action failed; continuing", exc_info=True)

    try:
        estimate = await estimator.estimate(text)
    except MacroEstimatorError:
        logger.exception("Macro estimation failed for %r", text)
        await message.answer(strings.MASA_LLM_ERROR)
        return

    if estimate is None:
        await message.answer(strings.MASA_UNPARSEABLE)
        return

    today = datetime.now(tz).date()
    async with sessionmaker() as session:
        await repository.add_meal(
            session,
            telegram_user_id=message.from_user.id,
            log_date=today,
            raw_text=text,
            estimate=estimate,
        )
        day = await repository.get_day_totals(
            session, telegram_user_id=message.from_user.id, log_date=today
        )
        profile = await repository.get_profile(session, message.from_user.id)
        reply = strings.format_meal_logged(estimate, day, profile)

    await message.answer(reply)
