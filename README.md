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

## Create the bot (BotFather)

1. In Telegram, open [@BotFather](https://t.me/BotFather) and send `/newbot`. Choose a name and a username ending in `bot`. Copy the **token** it gives you into `BOT_TOKEN`.
2. **Turn group privacy OFF** so the bot receives every message and photo caption in the group (not just commands addressed to it):
   - Send `/setprivacy` to BotFather → pick your bot → choose **Disable**.
   - If the bot was already in the group, **remove and re-add it** so the new setting takes effect.
3. Add the bot to the group (owner + tracked user + bot).
4. Get the tracked user's numeric id by messaging [@userinfobot](https://t.me/userinfobot), and put it in `TRACKED_USER_ID`. While testing yourself, use **your own** id so the bot replies to you.

> The bot only ever responds to the configured `TRACKED_USER_ID`; messages from anyone else in the group are ignored.

## Running locally

Requires Python 3.12+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"        # app + dev tools (ruff, black)

cp .env.example .env           # then edit .env with your real values
python -m daytracker           # starts long-polling; Ctrl+C to stop
```

On first start the SQLite database file (`DATABASE_PATH`, default `daytracker.db`) is created automatically. Send `/start` or `/ajutor` in the group to check it responds.

### Lint & format

```bash
ruff check .
black --check .
```

## Documentation

- `PLAN.md` — phased roadmap
- `DECISIONS.md` — architectural choices (append-only)
- `KNOWN_ISSUES.md` — active bugs / gotchas
- `SESSION_LOG.md` — date-stamped work log
- `CLAUDE.md` — rules for the AI engineer

## Status

**Phase 1 — Skeleton. IN PROGRESS.** Scaffold built: config, async DB bootstrap, long-polling bot, `/start` + `/ajutor` in Romanian. Pending a live run with a real token in the group.
