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
