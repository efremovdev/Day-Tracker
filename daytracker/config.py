"""Configuration loading.

All runtime configuration comes from environment variables (optionally loaded from
a local ``.env`` file). Secrets are never hard-coded. ``load_settings`` fails fast
with a clear message when something required is missing or invalid.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv

DEFAULT_TIMEZONE = "Europe/Bucharest"
DEFAULT_DATABASE_PATH = "daytracker.db"
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_MACRO_PROVIDER = "gemini"
# Ordered fallback chain: the estimator tries each model in turn and moves to the
# next one when a model hits its free-tier quota (HTTP 429). Free tier gives each
# model its own quota bucket, so a second model buys more daily headroom.
DEFAULT_GEMINI_MODELS = "gemini-2.5-flash,gemini-2.0-flash"
VALID_MACRO_PROVIDERS = ("gemini", "fake")


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated application settings."""

    bot_token: str
    tracked_user_id: int
    timezone: str
    gemini_api_key: str | None
    macro_provider: str
    gemini_models: tuple[str, ...]
    database_path: Path
    log_level: str

    @property
    def database_url(self) -> str:
        """Async SQLAlchemy URL for the SQLite database."""
        return f"sqlite+aiosqlite:///{self.database_path}"


def _require(name: str, value: str | None) -> str:
    if value is None or not value.strip():
        raise ConfigError(f"Missing required environment variable: {name}")
    return value.strip()


def load_settings(env_file: str | os.PathLike[str] | None = ".env") -> Settings:
    """Load and validate settings from the environment.

    If ``env_file`` exists it is loaded first (real environment variables still win).
    """
    if env_file is not None:
        load_dotenv(env_file)

    bot_token = _require("BOT_TOKEN", os.getenv("BOT_TOKEN"))

    raw_user_id = _require("TRACKED_USER_ID", os.getenv("TRACKED_USER_ID"))
    try:
        tracked_user_id = int(raw_user_id)
    except ValueError as exc:
        raise ConfigError(
            "TRACKED_USER_ID must be an integer (the user's numeric Telegram id)."
        ) from exc

    timezone = os.getenv("TIMEZONE", DEFAULT_TIMEZONE).strip() or DEFAULT_TIMEZONE
    try:
        ZoneInfo(timezone)
    except ZoneInfoNotFoundError as exc:
        raise ConfigError(f"Unknown TIMEZONE: {timezone!r} (use an IANA name).") from exc

    gemini_api_key = (os.getenv("GEMINI_API_KEY") or "").strip() or None

    macro_provider = (
        os.getenv("MACRO_PROVIDER", DEFAULT_MACRO_PROVIDER).strip() or DEFAULT_MACRO_PROVIDER
    ).lower()
    if macro_provider not in VALID_MACRO_PROVIDERS:
        raise ConfigError(
            f"MACRO_PROVIDER must be one of {', '.join(VALID_MACRO_PROVIDERS)} "
            f"(got {macro_provider!r})."
        )

    raw_models = os.getenv("GEMINI_MODELS", DEFAULT_GEMINI_MODELS).strip() or DEFAULT_GEMINI_MODELS
    gemini_models = tuple(name.strip() for name in raw_models.split(",") if name.strip())
    if not gemini_models:
        raise ConfigError("GEMINI_MODELS must list at least one model id.")

    database_path = Path(
        os.getenv("DATABASE_PATH", DEFAULT_DATABASE_PATH).strip() or DEFAULT_DATABASE_PATH
    ).expanduser()

    log_level = (os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).strip() or DEFAULT_LOG_LEVEL).upper()

    return Settings(
        bot_token=bot_token,
        tracked_user_id=tracked_user_id,
        timezone=timezone,
        gemini_api_key=gemini_api_key,
        macro_provider=macro_provider,
        gemini_models=gemini_models,
        database_path=database_path,
        log_level=log_level,
    )
