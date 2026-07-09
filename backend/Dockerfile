FROM python:3.12-slim

# guessit / building wheels need build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        gosu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

# /data = SQLite + config ; /media = mounted NAS media library
RUN mkdir -p /data /media

ENV PYTHONUNBUFFERED=1 \
    DB_PATH=/data/media_manager.db \
    MEDIA_ROOT=/media

# Start as root, drop privileges via gosu in entrypoint (PUID/PGID)
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
