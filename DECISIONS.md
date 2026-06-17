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
