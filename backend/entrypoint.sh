#!/bin/sh
set -e

# Drop privileges to PUID/PGID so files written to mounted NAS volumes
# don't end up owned by root (common Synology/QNAP pain point).
PUID="${PUID:-1000}"
PGID="${PGID:-1000}"

# Ensure a group+user with the requested id exists, then chown runtime dirs.
if [ "$(id -g appuser 2>/dev/null)" != "$PGID" ]; then
    groupmod -o -g "$PGID" appgroup 2>/dev/null || groupadd -o -g "$PGID" appgroup
    usermod -o -u "$PUID" -g "$PGID" appuser 2>/dev/null || useradd -o -u "$PUID" -g "$PGID" -M -d /app appuser
fi

chown -R "$PUID:$PGID" /data 2>/dev/null || true

exec gosu "$PUID:$PGID" "$@"
