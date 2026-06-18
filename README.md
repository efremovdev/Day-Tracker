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

## Macro estimation (Gemini)

Meals (`/masa ...`) are sent to an LLM that estimates calories and macros. The default
provider is **Google Gemini Flash** on the free tier:

1. Open [Google AI Studio](https://aistudio.google.com/apikey), create an API key, and put it in `GEMINI_API_KEY`.
2. `GEMINI_MODELS` is an ordered, comma-separated list of models to try. When a model
   hits its free-tier quota (HTTP 429), the bot automatically falls through to the next
   one — each model has its own quota, so listing two buys more daily headroom. Default:
   `gemini-2.5-flash,gemini-2.0-flash`.
3. `MACRO_PROVIDER` selects the backend: `gemini` (default) or `fake` — a deterministic
   offline stand-in that needs no API key, handy for local development without burning quota.

> Estimates are best-effort, not lab-accurate. Specifying grams in the caption
> (`100g piept de pui`) improves accuracy; vague meals are logged as approximate and flagged.

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

**Phase 3 — Meal logging + AI macro estimation. DONE.** `/masa <text>` (also as a photo caption) sends the description to Gemini, stores per-item macros, and replies with the breakdown, the meal total, and the running daily total vs target. Live acceptance passed.

**Next: Phase 4 — Activity, water, weight + corrections** (`/activitate`, `/apa`, `/cantar`, `/azi`, `/sterge`).

Done so far:
- **Phase 3 — Meal logging:** `/masa` text + photo-caption → Gemini macro estimation (swappable provider, ordered model-fallback on free-tier 429), stored per-item with running daily totals vs targets.
- **Phase 2 — Profile & targets:** `/profil` (guided onboarding) computes daily calorie + macro targets (Mifflin–St Jeor BMR → TDEE → goal adjustment); `/tinte` views and adjusts them.
- **Phase 1 — Skeleton:** config, async DB bootstrap, long-polling bot, `/start` + `/ajutor` in Romanian.
