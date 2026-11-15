# Trend Detective API, built for Google Cloud Run.
# Build context: this directory (backend/). Nothing outside it is needed at runtime:
# the engine reads NASA POWER over HTTPS and the demo cases live in api/demo_data/.
#
#   docker build -t trend-detective-api backend/
#   docker run --rm -p 8080:8080 -e FRONTEND_ORIGIN=http://localhost:3000 trend-detective-api

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8080

WORKDIR /app

# Runtime dependencies only (requirements-dev.txt is never installed).
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY trend_detective ./trend_detective
COPY api ./api

RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin app
USER 10001

EXPOSE 8080

# One process: Cloud Run scales by adding instances. `exec` makes uvicorn PID 1 so that it
# receives SIGTERM and closes the HTTP client cleanly. Cloud Run sets PORT.
CMD ["sh", "-c", "exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
