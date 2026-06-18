"""Activity, water, weight logging and the daily view (P4).

- ``/activitate <text>`` — log a free-text activity (logged only, no calorie
  add-back). Also works as a photo caption, like ``/masa``.
- ``/apa <ml>`` — log water; additive (the day's water is the sum of entries).
- ``/cantar <kg>`` — log a weigh-in; a tracking log only (never recomputes targets).
- ``/azi`` — today's meals + totals vs targets, plus activity, water, latest weight.

As with ``/masa``, aiogram's ``Command`` filter only matches ``message.text``, so the
``/activitate`` photo-caption path needs its own handler reading ``message.caption``.
"""

from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .. import repository, strings

router = Router(name="tracking")

# Input bounds, kept next to the matching error strings.
WATER_MIN_ML, WATER_MAX_ML = 1, 5000
WEIGHT_MIN, WEIGHT_MAX = 30.0, 300.0
# Cap the free-text activity description (P7 input validation); generous for normal use.
MAX_ACTIVITY_TEXT = 1000

# Matches an "/activitate" caption (optionally "/activitate@BotName") and captures the rest.
_ACT_CAPTION_RE = re.compile(
    r"^/activitate(?:@\w+)?(?:\s+(?P<args>.*))?$", re.IGNORECASE | re.DOTALL
)
# Tolerate a trailing unit on the numeric commands ("500 ml", "64,5 kg").
_WATER_RE = re.compile(r"^(\d+)\s*(?:ml)?$", re.IGNORECASE)
_KG_SUFFIX_RE = re.compile(r"\s*kg\s*$", re.IGNORECASE)


def _parse_weight(text: str) -> float | None:
    """Parse a weight in kg, accepting a Romanian comma and a trailing 'kg'."""
    cleaned = _KG_SUFFIX_RE.sub("", text.strip()).replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_water_ml(text: str) -> int | None:
    """Parse whole millilitres, tolerating a trailing 'ml'."""
    match = _WATER_RE.match(text.strip())
    return int(match.group(1)) if match else None


# --- /activitate (text + photo caption) ---------------------------------------


@router.message(Command("activitate"))
async def activitate_command(
    message: Message,
    command: CommandObject,
    sessionmaker: async_sessionmaker[AsyncSession],
    tz: ZoneInfo,
) -> None:
    await _log_activity(message, command.args, sessionmaker=sessionmaker, tz=tz)


@router.message(F.photo, F.caption.regexp(r"(?i)^/activitate(@\w+)?(\s|$)"))
async def activitate_caption(
    message: Message,
    sessionmaker: async_sessionmaker[AsyncSession],
    tz: ZoneInfo,
) -> None:
    match = _ACT_CAPTION_RE.match((message.caption or "").strip())
    args = match.group("args") if match else None
    await _log_activity(message, args, sessionmaker=sessionmaker, tz=tz)


async def _log_activity(
    message: Message,
    activity_text: str | None,
    *,
    sessionmaker: async_sessionmaker[AsyncSession],
    tz: ZoneInfo,
) -> None:
    text = (activity_text or "").strip()
    if not text:
        await message.answer(strings.ACTIVITATE_EMPTY)
        return
    if len(text) > MAX_ACTIVITY_TEXT:
        await message.answer(strings.ACTIVITATE_TOO_LONG)
        return
    today = datetime.now(tz).date()
    async with sessionmaker() as session:
        await repository.add_activity(
            session, telegram_user_id=message.from_user.id, log_date=today, text=text
        )
    await message.answer(strings.format_activity_logged(text))


# --- /apa ---------------------------------------------------------------------


@router.message(Command("apa"))
async def apa_command(
    message: Message,
    command: CommandObject,
    sessionmaker: async_sessionmaker[AsyncSession],
    tz: ZoneInfo,
) -> None:
    ml = _parse_water_ml(command.args or "")
    if ml is None or not (WATER_MIN_ML <= ml <= WATER_MAX_ML):
        await message.answer(strings.ERR_APA)
        return
    today = datetime.now(tz).date()
    async with sessionmaker() as session:
        await repository.add_water(
            session, telegram_user_id=message.from_user.id, log_date=today, ml=ml
        )
        total = await repository.get_day_water_ml(
            session, telegram_user_id=message.from_user.id, log_date=today
        )
    await message.answer(strings.format_water_logged(ml, total))


# --- /cantar ------------------------------------------------------------------


@router.message(Command("cantar"))
async def cantar_command(
    message: Message,
    command: CommandObject,
    sessionmaker: async_sessionmaker[AsyncSession],
    tz: ZoneInfo,
) -> None:
    weight = _parse_weight(command.args or "")
    if weight is None or not (WEIGHT_MIN <= weight <= WEIGHT_MAX):
        await message.answer(strings.ERR_CANTAR)
        return
    today = datetime.now(tz).date()
    async with sessionmaker() as session:
        await repository.add_weight(
            session, telegram_user_id=message.from_user.id, log_date=today, weight_kg=weight
        )
    await message.answer(strings.format_weight_logged(weight))


# --- /azi ---------------------------------------------------------------------


@router.message(Command("azi"))
async def azi_command(
    message: Message,
    sessionmaker: async_sessionmaker[AsyncSession],
    tz: ZoneInfo,
) -> None:
    user_id = message.from_user.id
    today = datetime.now(tz).date()
    async with sessionmaker() as session:
        meals = await repository.get_day_meals(session, telegram_user_id=user_id, log_date=today)
        day = await repository.get_day_totals(session, telegram_user_id=user_id, log_date=today)
        activities = await repository.get_day_activities(
            session, telegram_user_id=user_id, log_date=today
        )
        water_ml = await repository.get_day_water_ml(
            session, telegram_user_id=user_id, log_date=today
        )
        weight = await repository.get_latest_weight_today(
            session, telegram_user_id=user_id, log_date=today
        )
        profile = await repository.get_profile(session, user_id)
        text = strings.format_today(today, meals, day, activities, water_ml, weight, profile)
    await message.answer(text)
