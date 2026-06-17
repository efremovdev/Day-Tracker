# Claude Code Instructions

## Project context

DayTracker is a Romanian-language Telegram bot that helps **one** user track daily
nutrition and activity. She logs meals as a photo + caption starting with a keyword
(`/masa ...`); the bot reads **only the caption text** (the image is for human viewing,
never analyzed). An LLM estimates calories/protein/carbs/fat. The bot keeps personalized
daily targets, answers on-demand commands, and posts an automatic daily summary at 21:00
(Europe/Bucharest) plus a weekly report on Sunday.

Always read these at the start of every session before writing code:
- PLAN.md
- DECISIONS.md
- KNOWN_ISSUES.md
- SESSION_LOG.md

## Working agreement

- Implement only what the current phase requires. No scope creep.
- If a decision needs to be made that is not in DECISIONS.md, stop and ask the user.
- Update KNOWN_ISSUES.md when you discover bugs or workarounds.
- Update SESSION_LOG.md at the end of every session, dated.
- Never rewrite working code unless explicitly asked.
- Run lint/type/tests after changes. Fix errors before declaring done.
- Commit at logical milestones with clear messages. Never commit broken code.
- Stay strictly within the current [IN PROGRESS] phase.

## Topic discipline

This chat is dedicated to ONE phase only. If the user raises a topic unrelated to the
current phase: politely refuse, tell them to open a fresh chat for that work, offer a
short status of the current phase, and continue only on the current phase.

## Style

- Python 3.12+, full type hints, `from __future__ import annotations` where useful.
- Formatter: **black**; linter: **ruff**. Both must pass before "done".
- Async-first (aiogram 3). No blocking calls in handlers; wrap blocking I/O.
- All user-facing strings are **Romanian**. Keep them in one place (a strings module).
- Secrets only via environment / `.env` (never hard-coded, never committed).

## Stack constraints (locked — do not swap)

- aiogram 3.x for the Telegram layer.
- SQLite + SQLAlchemy 2.0 for persistence.
- APScheduler for scheduled summaries.
- LLM access goes through a single `MacroEstimator` interface. Default impl: Google
  Gemini Flash (free tier). Provider is selected by env var so it can be swapped for
  Claude/OpenAI later WITHOUT changing call sites.
- Long-polling (no webhooks) for the MVP.
- Only the configured user's messages are tracked (her Telegram user id in env).

## Romanian command set (target)

`/start`, `/profil`, `/tinte`, `/masa`, `/activitate`, `/apa`, `/cantar`, `/azi`,
`/sterge`, `/sumar`, `/saptamana`, `/ajutor`. Meal/activity commands must also work as a
photo caption.

## Current phase

See PLAN.md — phase marked [IN PROGRESS].
