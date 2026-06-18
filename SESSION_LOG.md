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

---

## 2026-06-18 — P1 closed

- User ran the live-token acceptance test: bot started with the real BotFather token,
  replied to `/start` and `/ajutor` in the group, and exited cleanly on Ctrl+C. ✅
- Re-verified the static gate before closing: `ruff check` and `black --check` both pass
  in `.venv`; working tree clean.
- **P1 marked [DONE 2026-06-18]** in PLAN.md. All acceptance criteria met.
- No phase is [IN PROGRESS] now (between phases). **Next:** open a fresh chat to start
  **P2: Profile & personalized targets** — it will claim P2 and flip it to [IN PROGRESS].

---

## 2026-06-18 — P2 Profile & personalized targets (implementation)

Claimed P2 (flipped to [IN PROGRESS]). Confirmed the open parameters with the user first
(see today's DECISIONS entry): goal adjustment −15%/0/+10%, macros 2.0 g/kg protein + 25%
fat + carbs remainder, `/tinte` adjusts total kcal.

Built profile onboarding + targets:
- `targets.py` — pure, I/O-free math: Mifflin–St Jeor BMR, TDEE × activity factor, goal
  adjustment, macro split. Enums `Sex`/`Activity`/`Goal`; `compute_targets`, `macros_for`.
- `models.py` — `Profile` ORM (inputs + computed targets + nullable `manual_kcal`), keyed by
  Telegram id. Registered for `create_all` via a local import in `init_db`.
- `repository.py` — async `get_profile` / `upsert_profile` / `update_targets` (all math stays
  in `targets.py`; this layer only reads/writes rows).
- `handlers/profile.py` — `/profil` FSM (sex → age → height → weight → activity → goal) with
  reply-keyboard choices + validated numeric text (Romanian comma); `/renunta` cancels;
  `/tinte` views targets and `/tinte <kcal>` overrides + recomputes macros.
- `strings.py` — all new Romanian text, label maps, and formatters in one place.
- `bot.py` — added FSM `MemoryStorage`, registered `profile.router`, and pass the
  `sessionmaker` to handlers via `start_polling` kwargs (contextual injection).

Verified: `ruff` + `black --check` pass; smoke test passes — target math vs hand calcs
(female/lose 1805 kcal · 130p/209c/50f, male/gain 3378, maintain 2124, and a `/tinte 1600`
override 130p/171c/44f); DB upsert + read across separate sessions; manual override sets
`manual_kcal`; re-running `/profil` clears it; Romanian formatters incl. diacritics;
dispatcher builds with the new router + storage.

**Pending (live acceptance):** user runs `/profil` end-to-end in Telegram and `/tinte`
(+ `/tinte 1600`) to confirm the conversation flow and that targets display correctly. P2
stays **[IN PROGRESS]** until that passes → then mark **[DONE]** in a fresh chat.

---

## 2026-06-18 — P2 closed

- User ran the live acceptance test: completed `/profil` end-to-end in Telegram, targets
  displayed correctly, and `/tinte` / `/tinte <kcal>` worked (view + override + recompute). ✅
- Re-verified the static gate before closing: `ruff` + `black --check` pass and the P2 smoke
  test passes; working tree clean.
- **P2 marked [DONE 2026-06-18]** in PLAN.md. All acceptance criteria met.
- No phase is [IN PROGRESS] now. **Next:** open a fresh chat to start **P3: Meal logging +
  AI macro estimation**.

---

## 2026-06-18 — P3 Meal logging + AI macro estimation (implementation)

Claimed P3 (flipped to [IN PROGRESS]). Confirmed the two open params with the user first
(see today's DECISIONS entry): vague input → **best-effort + flag**; and a **model
switcher** — an ordered Gemini model list that falls through on free-tier 429.

Built meal logging end-to-end:
- `estimator.py` — `MacroEstimator` protocol + `MacroItem`/`MealEstimate` dataclasses;
  pure `parse_estimate`/`loads_json_object` (recompute totals from items, tolerate ```json
  fences); `GeminiMacroEstimator` (official `google-genai`, async, JSON mode, ordered
  model fallback on `ClientError.code == 429`, lazy SDK import); deterministic
  `FakeMacroEstimator` for offline dev/tests; `create_estimator` factory by `MACRO_PROVIDER`.
- `models.py` — `Meal` (denormalized totals + `raw_text` + `approximate` + `note`,
  local `log_date`) and child `MealItem` (ordered per-food macros). Additive `create_all`.
- `repository.py` — `add_meal` + `get_day_totals` (SUM over user+date = running daily total)
  and a `DayTotals` DTO.
- `handlers/meals.py` — `/masa` as a text command **and** as a photo caption (dedicated
  `F.photo & F.caption.regexp` handler, since aiogram's `Command` ignores captions);
  estimate → store → reply with per-item breakdown, meal total, and daily total vs target.
  Empty → ask to describe; no food → ask to rephrase; backend down → Romanian error.
- `config.py` — `MACRO_PROVIDER` (gemini|fake, validated) + `GEMINI_MODELS` (ordered list).
- `bot.py` — build the estimator + tz, inject both as contextual kwargs, register
  `meals.router`. `.env.example` + README document the Gemini key / models / provider.
- `pyproject.toml` — added `google-genai>=1.0` (installed 2.8.0 in `.venv`; API surface
  verified: `client.aio.models.generate_content`, `GenerateContentConfig`, `errors.ClientError`).

Verified: `ruff` + `black --check` pass; offline smoke test passes — `parse_estimate`
(totals recomputed = 217 kcal, bad items dropped, whitespace note → None), fenced-JSON
parse, `FakeMacroEstimator` item split, `GEMINI_MODELS` parsing/trim, provider validation,
`create_estimator` (fake vs gemini-without-key → `ConfigError`), the full DB path (two
meals → running total updates correctly, **P3 acceptance**), other-day isolation, the
reply formatter (with/without profile), and dispatcher wiring (meals router registered).

Choices within P3 scope (no new architectural decisions needed): totals always summed from
items; whole-gram/kcal ints; one attempt per model (retry/backoff deferred to P7); meal
stored immediately (corrections via `/sterge` in P4).

**Pending (live acceptance):** user sets a real `GEMINI_API_KEY`, runs
`/masa 40g orez, 100g piept de pui`, confirms plausible macros + storage, sends a second
meal to confirm the running daily total updates, and tests a `/masa` **photo caption** in
the privacy-OFF group. P3 stays **[IN PROGRESS]** until that passes → then mark **[DONE]**.
