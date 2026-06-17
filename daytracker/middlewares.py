"""aiogram middlewares."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

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
