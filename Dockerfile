# DayTracker — single-user Romanian nutrition/activity Telegram bot.
# A long-polling worker: no inbound ports, outbound calls only (Telegram + Gemini).
FROM python:3.12-slim

# Don't write .pyc files; flush stdout/stderr so `docker compose logs` is live.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Run as a non-root user (created before /data so the named volume mounted there
# inherits this ownership on first creation — see docker-compose.yml).
RUN useradd --create-home --uid 10001 appuser

WORKDIR /app

# Install the package (and its runtime deps) into the image. Copy only what the
# build needs so the layer cache survives doc/compose edits.
COPY pyproject.toml ./
COPY daytracker ./daytracker
RUN pip install --no-cache-dir .

# Persistent data dir for the SQLite file. DATABASE_PATH is also pinned here as a
# default; docker-compose sets it authoritatively and mounts the volume at /data.
RUN mkdir -p /data && chown appuser:appuser /data
ENV DATABASE_PATH=/data/daytracker.db

USER appuser

CMD ["python", "-m", "daytracker"]
