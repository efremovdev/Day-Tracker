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

---

## 2026-06-18 — P3 closed

- User ran the live acceptance test (real `GEMINI_API_KEY`): `/masa` returned plausible
  macros and stored the meal, a second meal updated the running daily total correctly, and
  the `/masa` photo-caption path worked in the privacy-OFF group. ✅
- Re-verified the static gate before closing: `ruff` + `black --check` pass and the P3
  offline smoke test passes; working tree clean.
- **P3 marked [DONE 2026-06-18]** in PLAN.md. All acceptance criteria met.
- No phase is [IN PROGRESS] now. **Next:** open a fresh chat to start **P4: Activity,
  water, weight + corrections** (`/activitate`, `/apa`, `/cantar`, `/azi`, `/sterge`).

---

## 2026-06-18 — P4 Activity, water, weight + corrections (implementation)

Claimed P4 (flipped to [IN PROGRESS]). Confirmed the two open params with the user first
(see today's DECISIONS entry): `/sterge` removes the **last entry of any type** (shown in
a confirmation), and `/cantar` is a **tracking log only** (never recomputes targets).

Built the logging, daily view, and corrections:
- `models.py` — `ActivityLog`, `WaterLog`, `WeightLog` (each keyed by Telegram id +
  `log_date`, with `created_at`). Named `ActivityLog` to avoid clashing with
  `targets.Activity`. Additive `create_all`.
- `repository.py` — `add_activity` / `add_water` / `add_weight`; `get_day_meals` (for
  `/azi`), `get_day_activities`, `get_day_water_ml` (sum), `get_latest_weight_today`;
  plus corrections: `LastEntry` DTO, `get_last_entry` (newest row of each table, picks
  the overall newest by `created_at`) and `delete_entry` (meal also deletes its items via
  explicit DELETEs — no async lazy-load, no reliance on SQLite FK pragma).
- `handlers/tracking.py` — `/activitate` (text command **and** photo caption, like
  `/masa`), `/apa <ml>` (additive, tolerant of a trailing "ml"), `/cantar <kg>` (Romanian
  comma + trailing "kg" tolerated), `/azi` (today's meals + totals vs targets, activity,
  water, latest weight).
- `handlers/corrections.py` — `/sterge` with a reply-keyboard Da/Nu confirmation (no
  inline callbacks). The pending entry's kind+id is held in FSM state so "Da" deletes
  exactly what was shown; any other reply cancels. A meal delete also echoes the updated
  daily total.
- `strings.py` — all new Romanian text + `/azi` / confirm / done formatters; added an
  `_esc` HTML-escape helper, applied to user text shown in `/azi` and `/sterge`.
- `bot.py` — registered `tracking.router` and `corrections.router` (after meals).

Verified: `ruff` + `black --check` pass; offline smoke test passes — additive water sum,
activity/weight/meal logging, **last-entry ordering across all 4 types** with deletes,
**meal delete cascading to `meal_items` + daily totals dropping to zero (P4 acceptance)**,
the `/azi` formatter, HTML escaping of user text (`<3 lift & run` → escaped), the
`/sterge` confirm/done formatters, and dispatcher wiring (tracking + corrections
registered). HELP already listed all P4 commands (written in P1) — no change needed.

Choices within P4 scope (no new architectural decisions needed): explicit child-row
DELETE for meals; water tolerates a trailing unit; `/azi` shows today's weight only;
`/sterge` operates on the most-recent entry overall (not date-limited).

**Pending (live acceptance):** user logs `/activitate`, `/apa`, `/cantar`, checks `/azi`
shows them with totals vs targets, and runs `/sterge` to confirm it removes the right
entry (with confirmation) and totals update. Also confirm a `/activitate` **photo
caption** in the privacy-OFF group. P4 stays **[IN PROGRESS]** until that passes → then
mark **[DONE]**.

---

## 2026-06-18 — P4 closed

- User ran the live acceptance test: `/activitate`, `/apa`, and `/cantar` each logged
  correctly and appeared in `/azi` with running totals vs targets, and `/sterge` removed
  the right entry (with confirmation) and totals updated. ✅
- Re-verified the static gate before closing: `ruff` + `black --check` pass; working tree
  clean. (The P4 offline smoke test passed during implementation: additive water sum,
  cross-type last-entry ordering, meal delete cascading to items + totals, formatters,
  HTML escaping, dispatcher wiring.)
- **P4 marked [DONE 2026-06-18]** in PLAN.md. All acceptance criteria met.
- No phase is [IN PROGRESS] now. **Next:** open a fresh chat to start **P5: Daily summary**
  (`/sumar` on demand + the 21:00 Europe/Bucharest auto-summary via APScheduler).

---

## 2026-06-18 — P5 Daily summary (implementation)

Claimed P5 (flipped to [IN PROGRESS]). Confirmed the open params with the user first
(see today's DECISIONS entry): auto-summary goes to the **last chat she wrote in**
(remembered, zero config); an empty day still gets a **short nudge**; the encouraging
note is **canned, varied Romanian** seeded by the date (so `/sumar` and the scheduled
summary match); latest weight = **latest known across days**.

Built the daily summary, on demand and scheduled:
- `models.py` — `UserChat` (telegram id → last chat id), so the unsolicited 21:00 post
  has a destination. Additive `create_all`.
- `repository.py` — `remember_chat` / `get_chat_id`; `get_latest_weight` (across all
  days, vs the existing today-only helper); a `DaySummary` DTO (`is_empty` /
  `weighed_today` properties) and `get_day_summary` that gathers meals, totals,
  activity, water, latest weight, profile in one call — the single source both
  summaries read.
- `strings.py` — `format_summary` (header, kcal/macros vs targets %, per-meal list,
  activity, water, latest weight, note; empty-day → nudge), canned note buckets +
  `_pick_summary_note` (date-seeded, deterministic per day). User text HTML-escaped.
- `handlers/summary.py` — `/sumar` (replies with `format_summary` of `get_day_summary`).
- `middlewares.py` — `ChatRecorderMiddleware` (outer, after the tracked-user gate):
  records the chat of each tracked message; best-effort (never blocks handling).
- `scheduler.py` — `send_daily_summary` (looks up the chat, builds + posts the same
  summary; skips if no chat known; send errors logged, not fatal) and `create_scheduler`
  (`AsyncIOScheduler`, one `CronTrigger` 21:00 Europe/Bucharest, `coalesce`,
  `misfire_grace_time=3600`).
- `bot.py` — register `summary.router` + `ChatRecorderMiddleware`; build/start the
  scheduler before long-polling, shut it down in `finally`.
- `pyproject.toml` — added `APScheduler>=3.10,<4` (installed 3.11.2 in `.venv`).

Verified: `ruff` + `black --check` pass; offline smoke test passes — chat memory
(insert/no-op/update/read), latest-weight across-days vs today-only, **empty-day nudge**,
populated summary (totals, water sum, today-weight, 100 % → on-target note, HTML escape),
**scheduled job posts to the remembered chat and matches `/sumar` (deterministic note,
P5 acceptance)**, job **skipped when no chat recorded**, scheduler configured at
**hour=21 minute=0 tz=Europe/Bucharest**; plus dispatcher wiring (summary router + 2
outer middlewares) and the `ChatRecorderMiddleware` recording + chaining (and tolerating
a missing sessionmaker).

Choices within P5 scope (no new architectural decisions needed): one shared
gather+format path for both summaries; note seeded by date for same-day consistency;
scheduler in-process (no persistence — P7); destination skip when no chat is known yet.

**Pending (live acceptance):** user runs `/sumar` and confirms the summary is correct;
confirms the 21:00 auto-summary fires and matches `/sumar`; confirms it lands in the
expected chat (the one she last wrote in). P5 stays **[IN PROGRESS]** until that passes →
then mark **[DONE]**.

---

## 2026-06-18 — P5 closed

- User ran the live acceptance test: `/sumar` returned the correct daily summary, the
  21:00 Europe/Bucharest auto-summary fired, matched `/sumar`, and landed in the chat
  she last wrote in. ✅
- Re-verified the static gate before closing: `ruff` + `black --check` pass; working
  tree clean. (The P5 offline smoke test passed during implementation: chat memory,
  across-days vs today-only weight, empty-day nudge, populated summary + deterministic
  note, scheduled job → remembered chat matching `/sumar`, skip-when-no-chat, scheduler
  configured at 21:00 Europe/Bucharest, dispatcher + middleware wiring.)
- **P5 marked [DONE 2026-06-18]** in PLAN.md. All acceptance criteria met.
- No phase is [IN PROGRESS] now. **Next:** open a fresh chat to start **P6: Weekly
  report** (`/saptamana` on demand + the Sunday-night report).

---

## 2026-06-18 — P6 Weekly report (implementation)

Claimed P6 (flipped to [IN PROGRESS]). Confirmed the open params with the user first
(see today's DECISIONS entry): the window is the **ISO calendar week (Mon→reference
day)** — same rule for `/saptamana` (Mon→today) and the Sunday job (Mon→Sun); averages
divide by **all elapsed days** in the window (unlogged = 0); the Sunday report fires at
**21:00 after** the daily summary (one orchestrator job, sequential); best/worst =
**closest/furthest from the kcal target**.

Built the weekly report, on demand and scheduled:
- `repository.py` — `DayStat` (one calendar day's meal totals) + `WeekSummary` DTO
  (per-day stats, window weigh-ins, latest-weight fallback, profile; totals/averages
  and `is_empty` as properties). `get_week_summary` does one grouped per-day meal query
  over `Monday..end_date`, 0-fills unlogged days, pulls in-window weigh-ins (oldest→
  newest), latest weight, and the profile — the single source both paths read.
- `strings.py` — `format_weekly_report` (header + date range, `mese X/N zile`, daily
  averages vs targets %, days on/over/under target, best/worst day, weight trend) with
  helpers and `SAPTAMANA_EMPTY`. On-target band reuses the daily ±10 % thresholds
  (`_TARGET_UNDER`/`_TARGET_OVER`). Empty week → nudge; no-profile → averages + weight +
  `/profil` hint (target-relative sections omitted).
- `handlers/summary.py` — added `/saptamana` (replies with the shared formatter over
  `get_week_summary`); updated the module docstring (now daily P5 + weekly P6).
- `scheduler.py` — `send_weekly_report` (same gather+format, posts to the remembered
  chat) and a `send_evening_summaries` orchestrator: always the daily summary, then on
  Sundays the weekly report (sequential `await` → daily first; each send wraps its own
  errors). The 21:00 cron now calls the orchestrator (job id `daily_summary` →
  `evening_summaries`).
- `bot.py` — updated the scheduler start log to mention the Sunday weekly report. No
  new tables, no schema change, no new deps.

Verified: `ruff` + `black --check` pass; package imports clean; offline smoke test
passes — `get_week_summary` math (3 logged days of a seeded Mon–Sun week: avg 797
kcal/day, totals exclude prev/next-week meals; window weigh-ins 70→69), the populated
report (date range, `3/7 zile`, on/over/under = 1/1/1, best=Mon 99 %, worst=Wed 60 %,
trend `70 → 69 kg 📉 -1 kg`), **empty-week nudge**, **no-profile** report (no targets/
best-worst, `/profil` hint), **old-weigh fallback** ("fără cântăriri săptămâna asta"),
**mid-week window** (num_days shrinks to 3, future day excluded), and the **scheduler**
(Sunday → daily *then* weekly with the weekly matching `/saptamana`; non-Sunday → daily
only; `create_scheduler` builds one 21:00 `evening_summaries` job).

Choices within P6 scope (no new architectural decisions needed): one grouped query +
0-fill rather than 7 per-day reads; classification thresholds reuse the daily band;
P5's daily `_pick_summary_note` left untouched (no rewrite of working code).

**Pending (live acceptance):** user runs `/saptamana` and confirms the weekly report is
correct (averages, days on/over target, weight trend, best/worst day) over her real
week; confirms the Sunday-night auto-report fires at 21:00 after the daily summary and
matches `/saptamana`. P6 stays **[IN PROGRESS]** until that passes → then mark **[DONE]**.

---

## 2026-06-18 — P6 closed

- User ran the live acceptance test: `/saptamana` returned the correct weekly report
  (daily averages, days on/over target, weight trend, best/worst day), and the
  Sunday-night auto-report fires at 21:00 after the daily summary and matches
  `/saptamana`. ✅
- Re-verified the static gate before closing: `ruff` + `black --check` pass; working
  tree clean. (The P6 offline smoke test passed during implementation: week math,
  populated report, empty/no-profile/old-weigh edge cases, mid-week window, and the
  Sunday-vs-weekday scheduler gate with the weekly matching `/saptamana`.)
- **P6 marked [DONE 2026-06-18]** in PLAN.md. All acceptance criteria met.
- No phase is [IN PROGRESS] now. **Next:** open a fresh chat to start **P7: Hardening**
  (LLM failure/timeout/retry, input validation, restart safety, unit tests for target
  math + macro-JSON parsing).

---

## 2026-06-18 — P7 Hardening (implementation)

Claimed P7 (flipped to [IN PROGRESS]). Confirmed the three open params with the user
first (see today's DECISIONS entry): LLM transient failures → **retry then fall
through**; missed 21:00 summary → **catch up on startup, idempotently**; FSM state →
**stays in-memory** (accepted, documented).

Built the hardening:
- `estimator.py` — per-model **retry with exponential backoff** for transient failures
  (timeout/5xx/connection): up to `RETRY_ATTEMPTS` (2) attempts per model, `~1s` backoff,
  then fall through. 429 still moves straight to the next model (no retry); other 4xx
  still fail fast; a non-JSON response still falls through.
- `models.py` — `SummaryDelivery` table (`kind` → `last_sent_date`), the per-day
  delivery marker. Additive `create_all`.
- `repository.py` — `get_summary_sent_date` / `mark_summary_sent` (idempotent upsert).
- `scheduler.py` — `send_daily_summary` / `send_weekly_report` are now **idempotent per
  day** (skip if already sent; mark on success), so the scheduled job, an APScheduler
  misfire, and the catch-up can't double-send. Added `run_startup_catchup`: on boot, if
  21:00 already passed today and today's summary wasn't sent, send it (plus the weekly on
  Sundays). Never back-sends a fully elapsed prior day.
- `bot.py` — registered a dispatcher-level `on_error` handler (any unhandled exception →
  one calm Romanian `GENERIC_ERROR` reply + logged traceback); call `run_startup_catchup`
  after the scheduler starts, before polling.
- `handlers/meals.py` — wrapped the best-effort `send_chat_action("typing")`; added a
  `MAX_MEAL_TEXT` (1000) length cap. `handlers/tracking.py` — `MAX_ACTIVITY_TEXT` cap.
- `strings.py` — `GENERIC_ERROR`, `MASA_TOO_LONG`, `ACTIVITATE_TOO_LONG`; HTML-escape the
  LLM item names + note in the `/masa` reply (the escaping gap carried since P4).
- `pyproject.toml` — added `pytest>=8.0` (dev) + `[tool.pytest.ini_options]` (testpaths).
- `tests/` — `test_targets.py` (12 tests: BMR/TDEE/goal_kcal/macros_for/compute_targets
  vs hand-computed values, carb clamp, factor-table coverage, lose<maintain<gain) and
  `test_estimator.py` (parsing: fenced/plain JSON, non-object → None, `_to_int`/`_to_grams`
  coercions, totals recomputed from items, junk items dropped, negatives clamped, note
  trimmed). **56 tests pass.**

Verified: `ruff` + `black --check` pass; **56 unit tests pass**; package imports clean;
dispatcher builds with the error handler registered. Offline smoke test passes — estimator
**retry-then-success** (m1,m1), **429 fall-through** (m1,m2 — no same-model retry),
**400 fail-fast** (m1 only), **all-transient exhausts the chain** (m1,m1,m2,m2 → error);
restart safety: **idempotent daily send** (1 send across 2 calls), **catch-up gated on
21:00** (no send at 14:00, one send at 22:00, idempotent on re-run), **Sunday catch-up →
daily + weekly**.

Choices within P7 scope (no new architectural decisions needed): single shared LLM
timeout (no per-model tuning); catch-up reuses `send_evening_summaries` (the Sunday gate
lives there); tests cover only the plan's two pure areas (target math + macro-JSON), no
async/DB test harness added.

**Pending (live acceptance):** user confirms the bot survives bad input (a malformed
`/masa`/`/apa`/`/cantar` gets a friendly message, no crash) and a **restart with data
intact** (logs persist; if restarted after a missed 21:00, the catch-up sends today's
summary once). P7 stays **[IN PROGRESS]** until that passes → then mark **[DONE]**.

---

## 2026-06-18 — P7 closed

- User ran the live acceptance test: the bot survives bad input (malformed
  `/masa`/`/apa`/`/cantar` get a friendly message, no crash) and a restart with data
  intact (logs persist; the catch-up sends a missed 21:00 summary once on boot). ✅
- Re-verified the static gate before closing: `ruff` + `black --check` pass and the
  **56 unit tests pass**; working tree clean. (The P7 offline smoke test passed during
  implementation: estimator retry/fall-through/fail-fast/chain-exhaust, and restart
  safety — idempotent sends, catch-up gated on 21:00, Sunday daily+weekly.)
- **P7 marked [DONE 2026-06-18]** in PLAN.md. All acceptance criteria met.
- No phase is [IN PROGRESS] now. **Next:** open a fresh chat to start **P8: Deployment**
  (Dockerfile + run-as-worker, free 24/7 host, secrets/env, deploy guide) — runs 24/7
  in the cloud and survives a redeploy without losing data.

---

## 2026-06-18 — P8 Deployment (implementation)

Claimed P8 (flipped to [IN PROGRESS]). The one open parameter — the **host** (deferred
to P8 by the 2026-06-17 Hosting entry) — was finalized with the user (no preference, so
chosen on the "free 24/7" requirement; see today's DECISIONS entry): **Oracle Cloud
Always Free VM running Docker**, picked over Fly.io because Fly's free allowance ended in
2024 (now usage-based, ~$2/mo — not reliably $0, the same reason Railway/Render were
dropped). The deploy guide is a generic Ubuntu-VM + Docker flow, so it transfers to a
Google Cloud `e2-micro` (or any always-on VM) if Oracle ARM capacity is unavailable.

Built the deployment artifacts (no app code/schema change — pure ops):
- `Dockerfile` — single-stage `python:3.12-slim`, non-root user (uid 10001),
  `pip install .`, `CMD python -m daytracker`. Creates `/data` owned by the user (so a
  fresh named volume inherits writable ownership) and pins `DATABASE_PATH=/data/daytracker.db`.
- `docker-compose.yml` — `bot` service, `env_file: .env`, `restart: unless-stopped`,
  named volume `daytracker-data:/data`, and `DATABASE_PATH` set in `environment:` (wins
  over `.env`) so a redeploy can never relocate the DB onto the ephemeral layer.
- `.dockerignore` — keeps secrets (`.env`), data (`*.db`), venv, caches, tests and docs
  out of the image/build context.
- `.env.example` — note that Docker overrides `DATABASE_PATH` to the volume path.
- `README.md` — new **Deployment** section (Docker quickstart, redeploy/stop/restart,
  auto-restart, Oracle Always Free VM provisioning, backups); updated the Hosting line
  and the stale Status block (was Phase 5 → now Phase 8 IN PROGRESS, P5–P7 listed done).

Long-polling is outbound-only, so the host needs **no inbound ports, no public URL, no
TLS** — recorded in DECISIONS as a deploy simplification.

Verified: `ruff` + `black --check` pass and the **56 unit tests pass** (no Python
changed, re-run per the working agreement). Docker isn't installed on the dev Mac, so the
image build is deferred to live acceptance; as a proxy, `pip wheel . --no-deps` builds the
package cleanly (validating the Dockerfile's `pip install .` step, entry point and package
layout). Confirmed `.env` and `daytracker.db` are gitignored and not staged.

Choices within P8 scope (no new architectural decisions beyond the host): named volume
(not bind mount) so non-root ownership "just works"; `restart: unless-stopped` (crash +
reboot, honors manual stop); containerized over bare systemd (pins runtime + one-line
redeploy).

**Pending (live acceptance):** user provisions the VM, installs Docker, clones the repo,
fills `.env`, runs `docker compose up -d --build`, confirms the bot polls 24/7, and
confirms a redeploy (`git pull && docker compose up -d --build`) preserves the logged
data. P8 stays **[IN PROGRESS]** until that passes → then mark **[DONE]**.

**Update (same day) — host changed Oracle → Azure B1s, and repo pushed.**
- Pushed the code to a private GitHub repo, `efremovdev/Day-Tracker` (SSH remote, the
  user's existing key authenticates as `efremovdev`). Installed `gh` via brew along the
  way (not strictly needed once the repo existed). README clone step now uses the real
  URL + a read-only deploy-key step for the private repo.
- After walking the free-host landscape with the user (truly-free-forever VMs vs 12-month
  tiers vs PaaS that sleep), the user chose **Azure B1s** over the Oracle pick. Recorded
  as a superseding DECISIONS entry (host only; Docker/compose/persistence unchanged) with
  the trade-off on the record: Azure B1s is free for **12 months only**, then ~$7–8/mo.
  Updated the README Deployment host steps (Azure portal + B1s + SSH-only inbound),
  Hosting line, Status block, and the KNOWN_ISSUES P8 note. No code/compose/schema change
  — the guide is host-agnostic, so the switch is provisioning-only.
