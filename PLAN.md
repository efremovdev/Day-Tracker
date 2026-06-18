# Plan

Phased roadmap. Status: [TODO] / [IN PROGRESS] / [DONE date] / [BLOCKED reason].
Only ONE phase is [IN PROGRESS] at a time.

---

## P1: Skeleton [DONE 2026-06-18]

Minimal working bot that connects to Telegram and responds in the group.

Requirements:
- Project scaffold: package layout, `requirements.txt`/`pyproject`, `.gitignore`, `.env.example`.
- Config loader (BOT_TOKEN, GEMINI_API_KEY placeholder, TRACKED_USER_ID, TIMEZONE).
- aiogram 3 bot via long-polling; structured logging.
- `/start` and `/ajutor` handlers responding in Romanian.
- SQLite database created on startup with empty schema migrations in place.
- README section: how to create the bot in BotFather and set privacy mode OFF.

Out of scope:
- Any LLM calls, meal parsing, targets, scheduling.

Acceptance:
- Bot starts locally with a real token and responds to `/start` and `/ajutor` in the group.
- DB file is created; app exits cleanly on Ctrl+C.
- `ruff` and `black --check` pass.

---

## P2: Profile & personalized targets [DONE 2026-06-18]

Onboarding to compute her daily calorie + macro targets.

Requirements:
- `/profil` FSM collecting: sex, age (or birth year), height (cm), weight (kg),
  activity level, goal (lose/maintain/gain).
- BMR via Mifflin–St Jeor; TDEE = BMR × activity factor; goal adjustment.
- Macro targets (protein g/kg, fat, carbs as remainder) with sensible defaults.
- Persist profile + computed targets; `/tinte` to view and adjust.

Acceptance:
- Completing `/profil` stores the profile and shows correct kcal + macro targets.
- Re-running `/profil` updates values; `/tinte` reflects them.

---

## P3: Meal logging + AI macro estimation [DONE 2026-06-18]

Core feature: turn a Romanian caption into stored macros.

Requirements:
- `MacroEstimator` interface + Gemini (free tier) implementation, selected by env var.
- Prompt returns strict JSON: per-item {name, grams, kcal, protein, carbs, fat} + totals.
- `/masa <text>` and photo-caption `/masa ...` → estimate, store meal, reply with
  per-item breakdown, meal total, and running daily total vs target.
- Graceful handling of ambiguous/unparseable input (ask to clarify or best-effort + note).

Acceptance:
- `/masa 40g orez, 100g piept de pui` returns plausible macros and stores the meal.
- A second meal updates the running daily total correctly.

---

## P4: Activity, water, weight + corrections [DONE 2026-06-18]

Requirements:
- `/activitate <text>` (log only, no calorie add-back).
- `/apa <ml>` water; `/cantar <kg>` weight.
- `/azi` lists today's entries with running totals vs targets.
- `/sterge` removes the last entry (with confirmation).

Acceptance:
- Each command logs correctly and appears in `/azi`.
- `/sterge` removes the right entry and totals update.

---

## P5: Daily summary [DONE 2026-06-18]

Requirements:
- `/sumar` on-demand summary.
- Scheduled auto-summary at 21:00 Europe/Bucharest (APScheduler).
- Content: kcal + protein/carbs/fat vs targets (with %), per-meal list, activity, water,
  latest weight, short encouraging note.

Acceptance:
- Scheduled summary fires at 21:00; `/sumar` output matches the same data.

---

## P6: Weekly report [DONE 2026-06-18]

Requirements:
- `/saptamana` on-demand + scheduled Sunday-night report.
- Content: daily kcal/macro averages, days on/over target, weight trend, best/worst day.

Acceptance:
- Weekly report is correct across a seeded test week.

---

## P7: Hardening [DONE 2026-06-18]

Requirements:
- Robust error handling (LLM failure/timeout/retry, malformed input, DB errors).
- Input validation; confirmation on destructive actions.
- Restart safety (no data loss; scheduler reschedules on boot).
- Unit tests for target math and macro-JSON parsing.

Acceptance:
- Bot survives bad input and a restart with data intact; tests pass.

---

## P8: Deployment — free cloud, 24/7 [IN PROGRESS]

Requirements:
- Dockerfile + run-as-worker config.
- Choose free host (default candidates: Fly.io free allowance or Oracle Always Free VM).
- Secrets/env management; auto-restart; deploy guide in README.

Acceptance:
- Bot runs 24/7 in the cloud and survives a redeploy without losing data.

---

## P9: Polish (optional) [TODO]

Requirements:
- matplotlib chart (calorie/macro/weight trend PNG) attached to the weekly report.
- Nicer formatting/emojis; varied motivational messages.

Acceptance:
- Weekly report includes a readable chart image.
