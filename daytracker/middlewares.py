"""aiogram middlewares."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from . import repository

logger = logging.getLogger(__name__)


class TrackedUserMiddleware(BaseMiddleware):
    """Ignore any message that is not from the single tracked user.

    The bot lives in a group chat where other people also talk; only the
    configured user's messages are ever handled (see DECISIONS.md). While
    testing locally, set ``TRACKED_USER_ID`` to your own Telegram id.
    """

    def __init__(self, tracked_user_id: int) -> None:
        self.tracked_user_id = tracked_user_id

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message):
            user = event.from_user
            if user is None or user.id != self.tracked_user_id:
                return None
        return await handler(event, data)


class ChatRecorderMiddleware(BaseMiddleware):
    """Remember the chat the tracked user last wrote in (for the scheduled summary).

    Registered as an outer middleware *after* the tracked-user gate, so it only runs
    for the tracked user and on every message (before filters). The scheduled 21:00
    summary is unsolicited and needs a destination chat id; ``/sumar`` just replies,
    so it doesn't depend on this. Recording is best-effort — a write failure is logged
    and never blocks message handling. ``sessionmaker`` arrives via workflow_data.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.from_user is not None:
            sessionmaker: async_sessionmaker[AsyncSession] | None = data.get("sessionmaker")
            if sessionmaker is not None:
                try:
                    async with sessionmaker() as session:
                        await repository.remember_chat(
                            session,
                            telegram_user_id=event.from_user.id,
                            chat_id=event.chat.id,
                        )
                except Exception:  # never let chat recording break handling
                    logger.warning("Failed to record chat id", exc_info=True)
        return await handler(event, data)
