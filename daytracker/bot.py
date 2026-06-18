"""Bot wiring and the long-polling run loop."""

from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from .config import Settings, load_settings
from .db import dispose_engine, get_sessionmaker, init_db
from .handlers import common, profile
from .logging_setup import configure_logging
from .middlewares import TrackedUserMiddleware

logger = logging.getLogger(__name__)


def create_dispatcher(settings: Settings) -> Dispatcher:
    """Build the dispatcher: FSM storage, the tracked-user gate, and routers."""
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.outer_middleware(TrackedUserMiddleware(settings.tracked_user_id))
    dp.include_router(common.router)
    dp.include_router(profile.router)
    return dp


async def run_bot() -> None:
    """Configure everything and run the bot until interrupted."""
    settings = load_settings()
    configure_logging(settings.log_level)
    logger.info("Starting DayTracker (tracked user id: %s)", settings.tracked_user_id)

    await init_db(settings)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = create_dispatcher(settings)
    sessionmaker = get_sessionmaker(settings)

    try:
        # Long-polling only (no webhooks); drop anything queued while we were down.
        await bot.delete_webhook(drop_pending_updates=True)
        # ``sessionmaker`` is propagated to handlers as a contextual kwarg.
        await dp.start_polling(bot, sessionmaker=sessionmaker)
    finally:
        await bot.session.close()
        await dispose_engine()
        logger.info("Bot stopped.")
