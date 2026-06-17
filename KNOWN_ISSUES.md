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
