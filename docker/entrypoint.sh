#!/bin/sh
set -e

# All-in-one entrypoint: prepare a runtime user for file-ownership parity
# with the NAS mount, then hand off to supervisord (which starts nginx +
# uvicorn). supervisord must run as root, so we DON'T gosu it — the gosu
# drop happens per-program inside supervisord.conf for uvicorn only.

PUID="${PUID:-1000}"
PGID="${PGID:-1000}"

# Ensure a group+user with the requested id exists.
if [ "$(id -g appuser 2>/dev/null)" != "$PGID" ]; then
    groupmod -o -g "$PGID" appgroup 2>/dev/null || groupadd -o -g "$PGID" appgroup
    usermod -o -u "$PUID" -g "$PGID" appuser 2>/dev/null || useradd -o -u "$PUID" -g "$PGID" -M -d /app appuser
fi

# Own the persistent state dir so SQLite/WAL writes succeed.
chown -R "$PUID:$PGID" /data 2>/dev/null || true

exec "$@"
