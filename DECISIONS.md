# Decisions

Append-only log. Never delete entries; supersede with new dated entries if needed.

---

## 2026-06-17 — Stack

- Python 3.12+ — strong async + LLM/Telegram ecosystem.
- aiogram 3.x — modern async Telegram framework.
- SQLite + SQLAlchemy 2.0 — zero-ops single-file DB; fine for one user, easy to back up.
- APScheduler — scheduled daily/weekly reports.
- Long-polling (no webhooks) for MVP — no public URL or TLS needed.

## 2026-06-17 — LLM provider (macro estimation)

- User has no Anthropic key and wants a **free** option to start.
- Default: **Google Gemini Flash (free tier, Google AI Studio)** — free at this volume,
  good Romanian, supports structured JSON output.
- Access goes through a single `MacroEstimator` interface chosen by env var, so Claude or
  OpenAI can be dropped in later with no call-site changes. (Claude = likely quality upgrade.)

## 2026-06-17 — Input & meal trigger

- Meals arrive as **photo + caption**; the bot reads **only the caption text**. The image
  is never analyzed (visual reference for humans only).
- A meal is recognized by **keyword command** (`/masa ...`), usable as a photo caption,
  so normal group chatter is never parsed as food. Activity uses `/activitate ...`.
- Language of all input/output: **Romanian**.

## 2026-06-17 — Targets & activity math

- Personalized targets: **Mifflin–St Jeor BMR × activity factor**, then goal adjustment
  (lose / maintain / gain). Macros: protein g/kg, fat share, carbs as remainder.
- Activity is **logged only** — no calorie add-back. The activity factor in TDEE already
  represents her usual activity, so adding exercise calories would double-count.

## 2026-06-17 — Reports & timezone

- Timezone **Europe/Bucharest**.
- Daily summary auto-sent at **21:00**; weekly report on **Sunday night**. Both also
  available on demand (`/sumar`, `/saptamana`).

## 2026-06-17 — Scope of v1

- In: one tracked user, meal/activity/water/weight logging, personalized targets,
  corrections, daily + weekly reports, free-cloud 24/7 hosting.
- Out (anti-decisions, explicitly OUT of scope):
  - Image-based food recognition (caption text only).
  - Calorie add-back from exercise.
  - Multi-user product features / UI (DB keeps a users table so it's cheap later).
  - Webhooks (long-polling only for MVP).
  - Paid LLM by default (swappable interface keeps the door open).

## 2026-06-17 — Hosting

- Free cloud, runs as a long-polling worker. Specific host finalized in P8; current
  candidates are Fly.io free allowance or an Oracle Always Free VM. Railway/Render are no
  longer reliably free for an always-on worker, so they are deprioritized.

## 2026-06-17 — Macro engine: LLM-only (evaluated DB/hybrid)

- Considered a nutrition database/API instead of / alongside the LLM: USDA FoodData
  Central, Open Food Facts (barcodes), and NL-nutrition APIs (Nutritionix/Edamam).
- **Decision: LLM-only for now.** Input is Romanian free-text home meals; the hard part
  (parsing + translating + matching messy text to DB rows) is exactly what the LLM
  removes, while DB strengths (exact branded/barcode macros) rarely apply to gram-based
  home logging. Pure-DB NL APIs are English, rate-limited and commercial — a worse fit.
- The `MacroEstimator` interface keeps a DB/hybrid layer (LLM parses → DB verifies, plus
  barcode lookups) available as a cheap future add if exact branded accuracy is ever wanted.

## 2026-06-18 — P2 profile & target parameters

Chosen with the user at the start of P2 (the formulas were already locked; these
pin the open parameters):

- **Goal adjustment is percentage-based:** lose = TDEE −15%, maintain = TDEE,
  gain = TDEE +10%. Picked over a flat ±500 kcal because a percentage scales with
  body size — a flat 500 can be an oversized deficit for a smaller person.
- **Activity factors** (standard Mifflin–St Jeor): sedentary 1.2, light 1.375,
  moderate 1.55, active 1.725, very active 1.9.
- **Macro defaults ("higher protein"):** protein **2.0 g/kg** body weight, fat
  **25%** of kcal, carbs the remainder.
- **`/tinte` adjusts the total kcal:** she sets a kcal number; protein stays
  (g/kg × weight), fat = 25% of the new kcal, carbs = remainder. Stored as
  `manual_kcal`; re-running `/profil` recomputes from inputs and clears it.
- **Profile collects age in years** (not birth year) — simplest to ask; she
  re-runs `/profil` to update.
- **Onboarding UX:** aiogram FSM with **reply-keyboard** choices for
  sex/activity/goal and validated text for age/height/weight. No inline
  callbacks, so the existing message-only tracked-user gate stays sufficient.
  Numeric input accepts a Romanian decimal comma (`64,5`).
- **Persistence:** a single `profiles` table keyed by Telegram user id
  (row-per-user keeps multi-user cheap later, per the v1 scope decision). FSM
  uses in-memory storage for now; restart safety is a P7 concern.

## 2026-06-18 — P3 meal logging & macro estimation

Confirmed with the user at the start of P3 (formulas/provider were already locked;
these pin the open parameters):

- **Vague/missing-portion input → best-effort + flag.** When a caption lacks grams
  or is vague, the model assumes a typical portion, logs the meal, and marks it
  `approximate` (shown with a ⚠️ note); she can `/sterge` if wrong. Chosen over
  asking-to-clarify because it keeps logging fast and friction-free. Truly
  unrecognizable text (no food) is *not* stored — the bot asks her to rephrase.
- **Model switcher (free-tier resilience).** Instead of a single model, the Gemini
  estimator takes an **ordered list** of models (`GEMINI_MODELS`, default
  `gemini-2.5-flash,gemini-2.0-flash`) and falls through to the next when one returns
  HTTP 429 (quota exhausted). Each model has its own free-tier quota bucket, so the
  chain buys more daily headroom — the user asked for this explicitly. Robust
  retry/backoff (timeouts, 5xx) stays a P7 concern; P3 does one attempt per model.
- **Provider selection.** `MACRO_PROVIDER` env var picks the backend: `gemini`
  (default) or `fake` (deterministic offline stand-in, no key — for local dev/tests).
  All access stays behind the `MacroEstimator` protocol, so Claude/OpenAI can drop in
  later with no call-site change (honors the 2026-06-17 LLM-interface decision).
- **SDK:** the official `google-genai` client (async via `client.aio`), JSON mode
  (`response_mime_type="application/json"`), imported lazily so non-Gemini paths and
  tests don't require the package.
- **Totals are recomputed from items**, never trusted from the model's own totals —
  the parser sums per-item kcal/macros. Numbers are stored as whole grams/kcal (ints),
  matching how targets are stored.
- **Day attribution:** each meal is stamped with the **local calendar date** in the
  configured timezone (`log_date`) at log time; the "running daily total" sums all
  meals sharing that date. Aligns with the 21:00 Europe/Bucharest daily summary (P5).
- **Schema:** `meals` (denormalized totals + `raw_text` + `approximate` + optional
  `note`) with child `meal_items` (per-food macros, ordered). Denormalized totals keep
  daily/weekly rollups cheap; `meal_items` preserves the per-item breakdown.
- **No confirmation step:** per the plan, a meal is estimated and stored immediately,
  then echoed back; corrections come via `/sterge` (P4).

## 2026-06-18 — P4 activity, water, weight & corrections

Confirmed with the user at the start of P4 (logging math/no-add-back were already
locked; these pin the open parameters):

- **`/sterge` removes the last entry of ANY type** (most recent meal / activity /
  water / weight, by `created_at`), not just the last meal. The confirmation shows
  exactly what will be deleted so she can decline if it isn't the one she meant.
  Picked over "last meal only" because it's a literal "undo my last log" and the
  confirmation makes deleting the wrong type safe. Not limited to today — it's the
  most recent entry overall.
- **`/sterge` confirmation is a reply-keyboard (Da/Nu)**, consistent with `/profil`
  and honoring the 2026-06-18 "no inline callbacks" decision (the message-only
  tracked-user gate stays sufficient). The pending entry's kind+id is held in FSM
  state, so it deletes exactly the entry it showed even if she logs more meanwhile.
- **`/cantar` is a tracking log only — it does NOT recompute targets.** Each weigh-in
  is its own row (history for the P6 weekly trend); `/azi` shows the latest. Targets
  change only via `/profil` (re-run) or `/tinte`. Keeps tracking and targets cleanly
  separated, matching "she re-runs `/profil` to update" (2026-06-18).
- **`/apa` is additive:** each `/apa <ml>` adds a row; the day's water is the sum.
  No water target exists (water isn't part of the profile/targets).
- **`/activitate` stores free text only** (no parsing, no calorie add-back per
  2026-06-17), and also works as a photo caption (like `/masa`) per the CLAUDE.md
  command set. The image is never analyzed.
- **Schema (additive):** `activities`, `water_logs`, `weight_logs` — each keyed by
  Telegram id + `log_date`, with `created_at` (used to find the "last entry").
  `create_all` adds them on next start; no migration, no data loss.
- **User text is HTML-escaped** where shown back (`/azi`, `/sterge` confirm) so a
  stray `<`/`&` in her caption can't break Telegram HTML parsing.

## 2026-06-18 — P5 daily summary

Confirmed with the user at the start of P5 (the 21:00 time and the content list were
already locked; these pin the open parameters):

- **Auto-summary destination — remember the last chat she wrote in.** The 21:00
  summary is unsolicited, so (unlike `/sumar`, which just replies) it needs a chat
  id. Chosen over a fixed `SUMMARY_CHAT_ID` env var or DM-only: a tiny `user_chats`
  table records the chat of each incoming message (via an outer
  `ChatRecorderMiddleware` that runs only for the tracked user), and the job posts
  there — zero config, and it follows her between the group and a private chat. If
  she has never written, the job logs and skips (nothing to send to).
- **Empty day → still send a short nudge.** On a day with nothing logged, the 21:00
  summary fires anyway with a brief "n-ai înregistrat nimic / mâine reluăm" message,
  keeping the daily habit and acting as a reminder. "Empty" means nothing logged
  *today* (a weigh-in from an earlier day doesn't count).
- **Encouraging note — canned, varied Romanian, no LLM.** A small set of notes,
  bucketed by kcal vs target (<90 % under, 90–110 % on target, >110 % over; a
  no-profile bucket prompts `/profil`). The pick is **seeded by the date** so
  `/sumar` and the scheduled summary show the *same* note for a given day (P5
  acceptance: "output matches the same data") while still varying day to day.
  Richer/randomised motivation stays a P9 concern.
- **Latest weight = latest known across all days** (not today-only like `/azi`),
  per the KNOWN_ISSUES note that deferred "latest known weight" to P5/P6. Shown with
  its date when it isn't from today.
- **One shared path for both summaries.** `repository.get_day_summary` gathers the
  day's data into a `DaySummary` DTO and `strings.format_summary` renders it; both
  `/sumar` and the scheduler call exactly these, so the two outputs are identical.
- **Scheduler:** APScheduler `AsyncIOScheduler` in the bot's own loop, one
  `CronTrigger(hour=21, minute=0, tz=Europe/Bucharest)` job, started before
  long-polling and shut down on exit. Jobs are not persisted, so a run missed
  because the process was *down* at 21:00 is not replayed — restart safety is P7.

## 2026-06-18 — P6 weekly report

Confirmed with the user at the start of P6 (the "weekly report on Sunday night" and
the content list — averages, days on/over target, weight trend, best/worst day — were
already locked; these pin the open parameters):

- **Week window = the ISO calendar week (Mon–Sun), Europe/Bucharest.** Both paths use
  the *same* window: Monday of the current week through the report's reference day.
  On demand, `/saptamana` covers Monday → **today** (the week so far); the scheduled
  Sunday-night report runs on Sunday, so Monday → today is the **full Mon–Sun** that
  just ended — one rule, no special "previous week" case. Chosen over a rolling
  last-7-days window because "this week" matches how she thinks of it and the Sunday
  report lands cleanly on a completed week.
- **Averages count every elapsed day in the window (unlogged days = 0 kcal), not only
  days she logged.** The denominator is the number of days from Monday through the
  reference day (7 on Sunday, fewer mid-week) — *not* a fixed 7, so a mid-week
  `/saptamana` isn't dragged down by days that haven't happened yet. (The user picked
  "all days, unlogged = 0" over "only days with meals"; applying it to the *elapsed*
  window is the faithful reading.) The report also shows `mese: X/N zile` so the
  logged-day count stays visible.
- **Days on/over/under target classify only days with at least one meal logged**, using
  the **same band as the daily note** (<90 % under, 90–110 % on target, >110 % over).
  An unlogged day is *not* counted as "under" — it's absent from the classification
  (shown via the `X/N zile` line instead), so "0 kcal because she didn't log" never
  masquerades as "ate too little". Needs a profile/target; omitted (with a `/profil`
  hint) when there's none.
- **Best / worst day = closest / furthest from the kcal target** by absolute %
  deviation (over OR under), among logged days. Respects her goal (a very-low day
  isn't "best"). Needs a profile; the section is omitted without one. With a single
  logged day, only "best" is shown (best == worst); identical-deviation ties also
  collapse to one line.
- **Weight trend = first → last weigh-in within the window** (delta with 📈/📉/➡️). One
  weigh-in shows the value only; none in the window falls back to the latest known
  weight across all days (with its date) and notes "fără cântăriri săptămâna asta";
  no weigh-in ever → "—".
- **Empty week → short nudge** (like the daily empty case). "Empty" = no meals **and**
  no weigh-ins in the window (the two things the weekly report is about; activity/water
  aren't part of the weekly content per the plan, so they don't keep a week from being
  "empty").
- **Sunday delivery — daily first, then weekly, both at 21:00.** The existing 21:00
  cron now calls one orchestrator (`send_evening_summaries`) that always sends the
  daily summary and, on Sundays, sends the weekly report right after (sequential
  `await`, so the order is guaranteed — two messages). Kept as one job rather than a
  second same-time cron so ordering is deterministic; the daily habit stays unbroken.
- **One shared path for both weekly outputs**, mirroring P5: `repository.get_week_summary`
  gathers a `WeekSummary` DTO (per-day stats + window weigh-ins + latest weight +
  profile) and `strings.format_weekly_report` renders it; both `/saptamana` and the
  scheduler call exactly these, so on-demand and scheduled reports are identical.

## 2026-06-18 — P7 hardening

Confirmed with the user at the start of P7 (the P7 scope — robust error handling,
input validation, restart safety, unit tests — was already locked; these pin the
open parameters):

- **LLM transient failures → retry, then fall through.** The Gemini estimator now
  makes up to **2 attempts per model** for *transient* failures (request timeout,
  5xx, connection error) with a short exponential backoff (~1s before the retry),
  then moves to the next model in the chain. **429 (quota) still falls straight
  through to the next model** (a retry won't restore the bucket), and other 4xx
  (bad key/request) still fail fast. Chosen over no-retry (loses a meal log on a
  single transient blip) and over aggressive retry (a real outage would make her
  wait 30s+ before the error). A non-JSON response still moves to the next model
  (a retry at temperature 0.2 would repeat it).
- **Missed 21:00 summary → catch up on startup, idempotently.** A new
  `summary_deliveries` table records the date each scheduled summary (`daily` /
  `weekly`) was last sent. The send functions self-guard: they skip if today's was
  already sent, so the scheduled job, an APScheduler misfire, and the startup
  catch-up can never double-send. On boot, if **21:00 has already passed today** and
  today's summary wasn't sent, it's sent then (plus the weekly on Sundays). A day
  that fully elapsed while the process was down is **never** back-sent (no stale
  prior-day summary). Chosen over "skip missed runs" because the daily habit is the
  point of the bot and this was the restart-safety gap repeatedly deferred to P7.
- **FSM state stays in-memory (`MemoryStorage`).** A restart mid-`/profil` or
  mid-`/sterge` loses the half-finished form and she re-runs the command — acceptable
  for one user, and the *logged* data (the "data intact" acceptance) already lives in
  SQLite. Chosen over persisting FSM (a custom/third-party storage layer to maintain
  for a rare event). Documented in KNOWN_ISSUES.
- **Errors surface as one generic Romanian message, never a silent failure.** A
  dispatcher-level error handler catches any unhandled exception in a handler (e.g. a
  DB error) and replies with a single calm Romanian "ceva n-a mers" message; the
  meal-estimation path keeps its own specific error/clarify messages. Free-text inputs
  (`/masa`, `/activitate`) are length-capped, and the older `/masa` reply now
  HTML-escapes LLM item names/notes (the escaping gap carried forward since P4).

## 2026-06-18 — P8 deployment (host finalized)

The P8 scope (Dockerfile + run-as-worker, free host, secrets/env, auto-restart,
deploy guide) was already locked; this finalizes the open parameter — the **host** —
which the 2026-06-17 Hosting entry deferred to P8. The user expressed no preference,
so the choice was made on the "free 24/7" requirement:

- **Host = Oracle Cloud Always Free VM (Ubuntu) running Docker.** Picked over Fly.io
  because **Fly.io's free allowance ended in 2024** — it is now usage-based, requires
  a card, and a single always-on machine costs ~$2/mo, i.e. not reliably $0 (the same
  reason Railway/Render were deprioritized in the 2026-06-17 entry). Oracle's Always
  Free tier is genuinely free **forever**. The deploy guide is a generic "Ubuntu VM +
  Docker" flow, so it transfers unchanged to a **Google Cloud `e2-micro` Always Free
  VM** (or any always-on VM) if Oracle ARM capacity is unavailable in the user's region
  — only the instance-provisioning steps differ. Not locked to one vendor.
- **Long-polling ⇒ no inbound ports, no public URL, no TLS.** The worker only makes
  *outbound* calls (Telegram getUpdates, Gemini), so the VM needs no open ingress and
  no reverse proxy — a real simplification over a webhook deploy and a reason to keep
  long-polling for hosting too (honors the 2026-06-17 long-polling decision).
- **Containerized, not bare-metal.** A single-stage `python:3.12-slim` image runs
  `python -m daytracker` as a **non-root** user; `docker compose` manages it. Chosen
  over a bare `systemd` + venv setup because the image pins the exact runtime and deps
  and makes "redeploy" a one-liner (`git pull && docker compose up -d --build`),
  identical on any host.
- **Persistence = a named Docker volume for the SQLite file.** The DB lives at
  `/data/daytracker.db` on a named volume (`daytracker-data`) that survives
  `up --build` / `down` (it is only removed with an explicit `down -v`), so a redeploy
  never loses data — the P8 acceptance. `DATABASE_PATH=/data/daytracker.db` is set in
  compose's `environment:` (which wins over `env_file`), so a stray `DATABASE_PATH` in
  the server `.env` can't accidentally relocate the DB onto the ephemeral container
  layer. The image creates `/data` owned by the non-root user, so the fresh named
  volume inherits writable ownership on first creation.
- **Auto-restart = `restart: unless-stopped`.** The container comes back after a crash
  (the process exits non-zero on an unhandled error → container exits → restart) and
  after a VM reboot (Docker enabled at boot), but honors a deliberate manual stop.
  Combined with the P7 startup catch-up, a reboot near 21:00 still delivers the day's
  summary once on the way back up.
- **Secrets via a host `.env`, never in the image.** `.env` is `.dockerignore`d and
  `.gitignore`d; compose reads it from the host at run time (`env_file: .env`). The
  image carries no token/key. `MACRO_PROVIDER=gemini` in production (the `fake`
  provider stays a local-dev/test aid).

## 2026-06-18 — P8 host changed to Azure B1s (supersedes Oracle pick above)

After reviewing the free-host landscape with the user, the host is changed from the
Oracle Always Free VM to an **Azure B1s VM**. This supersedes only the *host* choice in
the P8 entry above; everything else there stands unchanged (Docker + compose, non-root
image, SQLite on a named volume, `restart: unless-stopped`, no inbound ports, secrets via
a host `.env`).

- **Why Azure, and why over AWS.** The user prefers the Azure ecosystem. Between the two
  12-month free VMs considered (AWS `t3.micro`, Azure `B1s`), Azure was picked because its
  B-series burst credits don't surprise-bill for sustained CPU (AWS `t3` "unlimited" mode
  can), and its 12-month free VM offer is more clear-cut for a new account than AWS's 2025
  credit-based free-tier revamp.
- **Trade-off accepted, on the record.** Azure B1s is free for **12 months only**
  (750 h/mo = 24/7) plus a ~$200 / 30-day credit; afterward a B1s is ~$7–8/mo — i.e. **not
  free-forever**, and more than the Fly.io option rejected earlier. The user accepted this
  knowingly, preferring Azure for now. Because the deploy guide is host-agnostic
  (Ubuntu + Docker), moving later to a truly-free-forever VM (Oracle Always Free or a
  Google Cloud `e2-micro`) is a **provisioning-only** change — no app, compose, or schema
  changes.
- **No code/config/schema impact.** Only the README provisioning steps and this rationale
  change; the `Dockerfile`, `docker-compose.yml`, `.env` handling, and SQLite-on-named-
  volume persistence are identical on Azure.
