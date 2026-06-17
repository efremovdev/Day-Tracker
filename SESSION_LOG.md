# Session Log

Date-stamped log of work sessions.

---

## 2026-06-17 — Project bootstrap (planning)

- Detected **Mode A (greenfield)**: empty `DayTracker` folder, no git.
- Scoped the project with the user (food/activity nutrition bot for one Romanian-speaking
  friend, in a group chat).
- Key answers captured: meals as photo+caption (caption text only), keyword trigger
  (`/masa`, `/activitate`), AI macro estimation via a **free** LLM, personalized targets,
  activity logged with no calorie add-back, daily summary at **21:00** Europe/Bucharest,
  weekly report included, water + weight tracking, corrections (`/azi`, `/sterge`), only
  her tracked, single-user for now, free-cloud 24/7 hosting.
- Decided stack and the swappable LLM interface (default Google Gemini Flash free tier).
- Generated the 6 planning docs and a 9-phase roadmap (P1 Skeleton → P9 Polish).
- Evaluated a nutrition database/API vs the LLM; chose **LLM-only** (see DECISIONS). Plan unchanged.
- **Next:** user reviews/approves the plan; then start P1 (Skeleton) in a fresh chat.

---

## 2026-06-17 — P1 Skeleton (implementation)

Built the bot scaffold under `daytracker/`:
- `config.py` — env-based `Settings` loader (BOT_TOKEN, TRACKED_USER_ID, TIMEZONE,
  DATABASE_PATH, LOG_LEVEL, GEMINI_API_KEY placeholder). Fails fast with clear messages;
  validates the timezone via `zoneinfo`.
- `logging_setup.py` — structured logging config (one place).
- `db.py` — async SQLAlchemy 2.0 (aiosqlite) engine/session/`Base`. `init_db` creates the
  SQLite file and runs `create_all`; **no domain tables yet** — schema bootstrap in place,
  models start in P2.
- `strings.py` — all Romanian user-facing text in one module.
- `middlewares.py` — `TrackedUserMiddleware` ignores messages from anyone but the tracked user.
- `handlers/common.py` — `/start` and `/ajutor`, in Romanian.
- `bot.py` / `__main__.py` — long-polling run loop, clean shutdown, `python -m daytracker`.

Project files: `pyproject.toml` (deps + ruff/black config, `daytracker` console script),
`.gitignore`, `.env.example`. README: added the BotFather setup + **privacy-mode-OFF** steps
and local run / lint instructions.

Verified locally (Python 3.14 venv): `ruff check` and `black --check` pass; smoke tests
confirm settings loading, DB file creation (incl. nested dir), dispatcher wiring, the
tracked-user gate (tracked passes / others dropped), and config-error paths.

Choices made within P1 scope (no new architectural decisions needed):
- Flat `daytracker/` package + `pyproject.toml` (picked pyproject over requirements.txt).
- Async DB (aiosqlite) to honor async-first; no models yet.
- Added the tracked-user gate now since P1 already loads `TRACKED_USER_ID`. **Testing note:**
  set `TRACKED_USER_ID` to your own Telegram id locally so the bot replies to you.

**Pending (live acceptance):** run with a real BotFather token in the group and confirm
`/start` + `/ajutor` reply and Ctrl+C exits cleanly. P1 stays **[IN PROGRESS]** until that passes.
**Next:** user does the live-token test → mark P1 [DONE] → open a fresh chat for P2.
