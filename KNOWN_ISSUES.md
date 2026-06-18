# Known Issues

Active bugs, gotchas, workarounds. Append with date.

---

## 2026-06-17 — Risks noted at planning time (not yet bugs)

- **Free Gemini tier limits.** Rate limits / occasional unavailability are possible. Plan
  for retries and a clear Romanian error message. Revisit if volume grows.
- **LLM macro estimates are approximate.** Numbers are best-effort, not lab-accurate;
  surface them as estimates. Specifying grams in the caption improves accuracy.
- **Free 24/7 hosting is finicky.** Some "free" hosts sleep or expire credits. To be
  resolved in P8 (Fly.io / Oracle Always Free are the leading candidates).
- **Group privacy mode.** The bot must be added to the group with BotFather privacy mode
  set OFF so it reliably receives messages/captions. Document in P1 setup.
- **Photo-caption commands.** Confirm during P3 that a `/masa` command sent as a photo
  caption is delivered to the bot as expected in a privacy-off group.

## 2026-06-18 — P2 notes

- **FSM state is in-memory (`MemoryStorage`).** If the bot restarts mid-`/profil`, the
  half-finished form is lost and she must run `/profil` again. Acceptable for now;
  persistent FSM storage / restart safety is a P7 concern.
- **Unknown slash-commands during `/profil`.** A command with no handler yet (e.g. `/azi`
  before P4) typed mid-form is treated as the current step's input and rejected with the
  step's validation message. Implemented commands (`/start`, `/ajutor`, `/profil`,
  `/tinte`, `/renunta`) work mid-form. Harmless; revisit if it becomes confusing.
  - Note (P3): `/masa` typed mid-`/profil` is likewise swallowed by the active FSM step
    (profile router is matched before meals). Same harmless behavior; revisit in P7.

## 2026-06-18 — P3 notes

- **Photo-caption commands — resolved in code, live-confirm pending.** aiogram 3's
  `Command` filter only reads `message.text`, *not* `message.caption`, so a `/masa` photo
  caption would never reach a plain `Command("masa")` handler. P3 adds a dedicated handler
  matching `F.photo & F.caption.regexp(^/masa...)` and parses the args out of the caption.
  Verified by unit/smoke logic; still needs a real photo-with-caption test in the
  privacy-OFF group during live acceptance (the original KNOWN_ISSUES question).
- **Model fallback scope.** The Gemini estimator only falls through to the next model on
  HTTP **429** (quota). Other client errors (bad key, 400) fail fast with a Romanian
  message; timeouts/5xx also try the next model but there is **no** retry/backoff yet —
  that, plus per-model timeout tuning, is P7. If *all* models 429, she sees the generic
  "service unavailable" message.
- **`send_chat_action("typing")` is best-effort but not wrapped.** If that pre-call fails
  (rare network blip), the `/masa` handler errors before logging. Acceptable for P3;
  harden in P7 alongside the other error paths.
- **Schema is additive.** An existing `daytracker.db` from P1/P2 gains `meals` /
  `meal_items` via `create_all` on next start — no migration needed, no data loss.
- **LLM estimates remain approximate** (see planning risks above). Per-item grams in the
  caption improve accuracy; vague meals are flagged `approximate` in the reply.

## 2026-06-18 — P4 notes

- **`/sterge` confirmation is FSM-based; other commands can interrupt it.** While the
  Da/Nu confirmation is pending (`DeleteForm.confirm`), a command handled by an earlier
  router (`/masa`, `/azi`, `/apa`, `/cantar`, `/activitate`, `/profil`, `/tinte`) runs
  in any state and consumes that message, leaving the delete confirmation dangling; the
  next plain text then cancels it (anything other than the "Da" button cancels). Nothing
  is deleted unintentionally. Same family as the P2/P3 FSM-swallowing note; revisit in P7.
- **"Last entry" ties within the same second.** `created_at` is stored at SQLite's
  1-second resolution, so two entries logged in the same second tie; `get_last_entry`
  then breaks the tie by type order (meal → activity → water → weight), not true insert
  order. Not reachable in practice (one user typing commands seconds apart); revisit only
  if it ever matters.
- **`/sterge` is not limited to today.** It removes the most recent entry *overall* (any
  day, any type) — a literal "undo my last log". The confirmation shows exactly what it
  is, so an unexpected old entry can be declined.
- **`/azi` shows only today's weight.** If she didn't weigh in today, weight shows "—"
  even if an earlier weigh-in exists. The "latest known weight" across days is a daily/
  weekly-summary concern (P5/P6), kept out of the strictly-today `/azi` view.
- **User text is HTML-escaped in `/azi` and `/sterge`** (new in P4). The older `/masa`
  reply still interpolates LLM item names without escaping; harmless today (names come
  from the model) and out of P4 scope — note for a P7 hardening pass.
- **Schema is additive.** An existing `daytracker.db` gains `activities`, `water_logs`,
  and `weight_logs` via `create_all` on next start — no migration, no data loss.
