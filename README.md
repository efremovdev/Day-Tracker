# DayTracker

A Telegram bot that helps one person track daily nutrition and activity, in Romanian. She logs a meal as a photo + caption (e.g. `/masa 40g orez, 100g piept de pui`); the bot reads only the caption text, uses an LLM to estimate calories / protein / carbs / fat, tracks them against personalized daily targets, and posts a daily summary at 21:00 plus a weekly trend report.

## Stack

- **Python 3.12+** with [aiogram 3](https://docs.aiogram.dev) (async Telegram framework)
- **SQLite** via SQLAlchemy 2.0 (single-file persistence)
- **LLM macro estimation** behind a swappable provider — default **Google Gemini Flash (free tier)**; upgradeable to Claude or OpenAI with no rewrite
- **APScheduler** for the daily (21:00) and weekly (Sunday) reports
- **Timezone:** Europe/Bucharest
- **Hosting:** free cloud, running as a long-polling worker — Docker on an **Oracle Cloud Always Free VM** (see [Deployment](#deployment-247-on-a-free-cloud-vm))

## Who it's for

A single user (the owner's friend). She is the only tracked person; the bot lives in a small group (owner + her + bot) with Telegram privacy mode OFF.

## Create the bot (BotFather)

1. In Telegram, open [@BotFather](https://t.me/BotFather) and send `/newbot`. Choose a name and a username ending in `bot`. Copy the **token** it gives you into `BOT_TOKEN`.
2. **Turn group privacy OFF** so the bot receives every message and photo caption in the group (not just commands addressed to it):
   - Send `/setprivacy` to BotFather → pick your bot → choose **Disable**.
   - If the bot was already in the group, **remove and re-add it** so the new setting takes effect.
3. Add the bot to the group (owner + tracked user + bot).
4. Get the tracked user's numeric id by messaging [@userinfobot](https://t.me/userinfobot), and put it in `TRACKED_USER_ID`. While testing yourself, use **your own** id so the bot replies to you.

> The bot only ever responds to the configured `TRACKED_USER_ID`; messages from anyone else in the group are ignored.

## Macro estimation (Gemini)

Meals (`/masa ...`) are sent to an LLM that estimates calories and macros. The default
provider is **Google Gemini Flash** on the free tier:

1. Open [Google AI Studio](https://aistudio.google.com/apikey), create an API key, and put it in `GEMINI_API_KEY`.
2. `GEMINI_MODELS` is an ordered, comma-separated list of models to try. When a model
   hits its free-tier quota (HTTP 429), the bot automatically falls through to the next
   one — each model has its own quota, so listing two buys more daily headroom. Default:
   `gemini-2.5-flash,gemini-2.0-flash`.
3. `MACRO_PROVIDER` selects the backend: `gemini` (default) or `fake` — a deterministic
   offline stand-in that needs no API key, handy for local development without burning quota.

> Estimates are best-effort, not lab-accurate. Specifying grams in the caption
> (`100g piept de pui`) improves accuracy; vague meals are logged as approximate and flagged.

## Running locally

Requires Python 3.12+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"        # app + dev tools (ruff, black, pytest)

cp .env.example .env           # then edit .env with your real values
python -m daytracker           # starts long-polling; Ctrl+C to stop
```

On first start the SQLite database file (`DATABASE_PATH`, default `daytracker.db`) is created automatically. Send `/start` or `/ajutor` in the group to check it responds.

### Lint, format & test

```bash
ruff check .
black --check .
pytest                 # unit tests (target math + macro-JSON parsing)
```

## Deployment (24/7 on a free cloud VM)

The bot runs as a **long-polling worker** — it only makes *outbound* calls (Telegram +
Gemini), so the host needs **no open ports, no public URL, and no TLS**. It's packaged as
a Docker image and managed with `docker compose`; the SQLite database lives on a named
volume so it **survives a redeploy**.

### Run with Docker (any machine)

```bash
cp .env.example .env           # fill in BOT_TOKEN, TRACKED_USER_ID, GEMINI_API_KEY
docker compose up -d --build   # build + start in the background
docker compose logs -f         # follow logs (Ctrl+C to stop following)
```

`MACRO_PROVIDER` should be `gemini` in production. The DB path is set automatically by
`docker-compose.yml` to `/data/daytracker.db` on the `daytracker-data` volume — **don't**
override `DATABASE_PATH` in `.env` for the container.

- **Redeploy (new code):** `git pull && docker compose up -d --build` — the volume (and
  thus all logged data) is untouched.
- **Stop / start:** `docker compose down` keeps the data; `docker compose up -d` brings it
  back. Only `docker compose down -v` deletes the volume (and the database).
- **Auto-restart:** the container is set to `restart: unless-stopped`, so it comes back
  after a crash or a VM reboot. If a 21:00 summary was missed while the VM was down, the
  startup catch-up delivers it once on the way back up.

### Host: Oracle Cloud Always Free VM

Oracle's *Always Free* tier is genuinely free forever (unlike Fly.io's allowance, which
ended in 2024). The steps below are a generic "Ubuntu VM + Docker" flow — they work
unchanged on a **Google Cloud `e2-micro` Always Free** instance (or any always-on VM) if
Oracle's ARM capacity is unavailable in your region.

1. **Create the instance.** In the [Oracle Cloud Console](https://cloud.oracle.com/) →
   *Compute → Instances → Create instance*. Pick an **Always Free–eligible** shape
   (`VM.Standard.A1.Flex` ARM if available, otherwise `VM.Standard.E2.1.Micro` x86) and
   the **Ubuntu 22.04/24.04** image. Add your SSH public key. No ingress rules are needed
   (long-polling is outbound-only) — leave the default security list.
2. **SSH in:** `ssh ubuntu@<public-ip>`.
3. **Install Docker + the compose plugin** and enable it at boot:
   ```bash
   sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2 git
   sudo systemctl enable --now docker
   sudo usermod -aG docker $USER && newgrp docker   # run docker without sudo
   ```
4. **Get the code and configure secrets.** The repo is private, so let the VM read it
   with a read-only **deploy key**: on the VM run `ssh-keygen -t ed25519 -C daytracker-vm`
   (no passphrase), then add the printed `~/.ssh/id_ed25519.pub` at
   *GitHub → repo → Settings → Deploy keys → Add deploy key* (read access is enough). Then:
   ```bash
   git clone git@github.com:efremovdev/Day-Tracker.git daytracker && cd daytracker
   cp .env.example .env
   nano .env                      # set BOT_TOKEN, TRACKED_USER_ID, GEMINI_API_KEY
   ```
5. **Launch:** `docker compose up -d --build`, then `docker compose logs -f` to confirm
   it started (`Database ready…`, `Scheduler started…`, `Start polling`).

### Backups

The whole state is one SQLite file on the named volume. To copy it off the host:

```bash
docker compose cp bot:/data/daytracker.db ./daytracker-backup.db
```

## Documentation

- `PLAN.md` — phased roadmap
- `DECISIONS.md` — architectural choices (append-only)
- `KNOWN_ISSUES.md` — active bugs / gotchas
- `SESSION_LOG.md` — date-stamped work log
- `CLAUDE.md` — rules for the AI engineer

## Status

**Phase 8 — Deployment. IN PROGRESS.** The bot is containerized (`Dockerfile`) and runs as a 24/7 long-polling worker via `docker compose`, with the SQLite database on a named volume so a redeploy keeps all data. Target host is an **Oracle Cloud Always Free VM** (the steps work on any Ubuntu VM, e.g. a Google Cloud `e2-micro`). See [Deployment](#deployment-247-on-a-free-cloud-vm). (Pending live acceptance: running it in the cloud and confirming a redeploy preserves data.)

Done so far:
- **Phase 7 — Hardening:** LLM retry/backoff with model fall-through, a generic-error handler, restart-safe (idempotent, catch-up) summaries, input length caps, and unit tests (target math + macro-JSON parsing).
- **Phase 6 — Weekly report:** `/saptamana` on demand + the Sunday-night auto-report (daily averages vs targets, days on/over/under, weight trend, best/worst day).
- **Phase 5 — Daily summary:** `/sumar` on demand + the 21:00 Europe/Bucharest auto-summary, posted to the chat the user last wrote in.
- **Phase 4 — Activity, water, weight + corrections:** `/activitate` (text + photo caption), `/apa <ml>` (additive), `/cantar <kg>` (tracking only); `/azi` shows today's entries vs targets; `/sterge` removes the last entry of any type with a Da/Nu confirmation.
- **Phase 3 — Meal logging:** `/masa` text + photo-caption → Gemini macro estimation (swappable provider, ordered model-fallback on free-tier 429), stored per-item with running daily totals vs targets.
- **Phase 2 — Profile & targets:** `/profil` (guided onboarding) computes daily calorie + macro targets (Mifflin–St Jeor BMR → TDEE → goal adjustment); `/tinte` views and adjusts them.
- **Phase 1 — Skeleton:** config, async DB bootstrap, long-polling bot, `/start` + `/ajutor` in Romanian.
