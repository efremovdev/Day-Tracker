# DayTracker

A Telegram bot that helps one person track daily nutrition and activity, in Romanian. She logs a meal as a photo + caption (e.g. `/masa 40g orez, 100g piept de pui`); the bot reads only the caption text, uses an LLM to estimate calories / protein / carbs / fat, tracks them against personalized daily targets, and posts a daily summary at 21:00 plus a weekly trend report.

## Stack

- **Python 3.12+** with [aiogram 3](https://docs.aiogram.dev) (async Telegram framework)
- **SQLite** via SQLAlchemy 2.0 (single-file persistence)
- **LLM macro estimation** behind a swappable provider — default **Google Gemini Flash (free tier)**; upgradeable to Claude or OpenAI with no rewrite
- **APScheduler** for the daily (21:00) and weekly (Sunday) reports
- **Timezone:** Europe/Bucharest
- **Hosting:** free cloud, running as a long-polling worker (host finalized in P8)

## Who it's for

A single user (the owner's friend). She is the only tracked person; the bot lives in a small group (owner + her + bot) with Telegram privacy mode OFF.

## Documentation

- `PLAN.md` — phased roadmap
- `DECISIONS.md` — architectural choices (append-only)
- `KNOWN_ISSUES.md` — active bugs / gotchas
- `SESSION_LOG.md` — date-stamped work log
- `CLAUDE.md` — rules for the AI engineer

## Status

**Phase 1 — Skeleton. IN PROGRESS.** Planning docs complete; awaiting approval before code.
