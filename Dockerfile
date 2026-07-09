# =========================================================================
#  MediaManager — all-in-one image (nginx + FastAPI in one container)
#
#  Single exposed port (80). nginx serves the SPA and reverse-proxies
#  /api and /media to uvicorn on the loopback. supervisord keeps both
#  processes alive.
# =========================================================================

# ---------- stage 1: build the Vue frontend ----------
FROM node:22-alpine AS frontend-build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build          # → /app/dist

# ---------- stage 2: install Python deps to a clean prefix ----------
# Building guessit wheels needs gcc; we keep that here and only copy the
# installed packages to the runtime stage so build-essential stays out.
FROM python:3.12-slim AS backend-build
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- stage 3: runtime (nginx + uvicorn) ----------
FROM python:3.12-slim AS runtime

# runtime deps: nginx (frontend + proxy), gosu (privilege drop),
# supervisor (process manager). Clear the apt cache to slim the layer.
RUN apt-get update && apt-get install -y --no-install-recommends \
        nginx \
        gosu \
        supervisor \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/nginx/sites-enabled/default   # avoid Debian default on :80

# Python deps from the clean prefix.
COPY --from=backend-build /install /usr/local

WORKDIR /app
COPY backend/app /app/app

# Built frontend → nginx docroot.
COPY --from=frontend-build /app/dist /usr/share/nginx/html

# Our configs.
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Persistent state dirs. /data = SQLite + config, /media = NAS library mount.
RUN mkdir -p /data /media

ENV PYTHONUNBUFFERED=1 \
    DB_PATH=/data/media_manager.db \
    MEDIA_ROOT=/media

EXPOSE 80

ENTRYPOINT ["/entrypoint.sh"]
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
