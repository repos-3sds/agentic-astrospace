# ── Stage 1: build the Angular SPA ───────────────────────────────────────────
FROM node:22-slim AS ui-build
WORKDIR /app/ui
COPY ui/package.json ui/package-lock.json ./
RUN npm ci
COPY ui/ ./
# angular.json outputPath is ../frontend/dist → lands in /app/frontend/dist
RUN npm run build

# ── Stage 2: Python runtime ──────────────────────────────────────────────────
FROM python:3.12-slim
WORKDIR /app

# pyswisseph compiles its C extension from source — needs gcc during install
# only; purge it afterwards to keep the runtime image slim.
COPY requirements.txt ./
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential poppler-utils \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y build-essential \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY main.py setup.py ./
COPY astrospace/ ./astrospace/
COPY --from=ui-build /app/frontend/dist ./frontend/dist

# Run as an unprivileged user. The code stays root-owned (read-only to the
# app); only the working directory itself is the app's, for anything a
# library caches next to it. Temporary files go to /tmp as usual.
RUN useradd --system --uid 10001 --create-home --home-dir /home/app app \
    && chown app /app
USER app

# Cloud Run injects PORT; default to 8080 for local docker runs.
ENV PORT=8080
EXPOSE 8080
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT}
