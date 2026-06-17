"""Entry point: ``python -m daytracker``."""

from __future__ import annotations

import asyncio
import logging

from .bot import run_bot
from .config import ConfigError


def run() -> None:
    try:
        asyncio.run(run_bot())
    except ConfigError as exc:
        logging.basicConfig(level=logging.ERROR)
        logging.getLogger("daytracker").error("Configuration error: %s", exc)
        raise SystemExit(1) from exc
    except (KeyboardInterrupt, SystemExit):
        logging.getLogger("daytracker").info("Shutdown requested, exiting.")


if __name__ == "__main__":
    run()
