#!/bin/sh
set -e

# All-in-one entrypoint: prepare a runtime uid/gid that matches the NAS
# media directory's owner, so the backend can read/write the mount without
# the user having to figure out the right PUID/PGID by hand.
#
# Resolution order for the uid/gid we drop to:
#   1. PUID/PGID env vars if set explicitly → use them.
#   2. Else, if /media exists → adopt its owner uid/gid (auto-adapt).
#   3. Else fall back to 1000:1000.
# supervisord still runs as root; gosu drops uvicorn to the resolved uid:gid
# (see supervisord.conf). gosu accepts numeric ids, so no appuser needed.

PUID="${PUID:-}"
PGID="${PGID:-}"

# Auto-detect: if no explicit PUID/PGID, read the media mount's owner.
if [ -z "$PUID" ] || [ -z "$PGID" ]; then
    if [ -d /media ]; then
        DETECTED_UID=$(stat -c %u /media 2>/dev/null || echo "")
        DETECTED_GID=$(stat -c %g /media 2>/dev/null || echo "")
        if [ -n "$DETECTED_UID" ]; then
            # Adopt the media owner — including root (0). Many NAS mounts
            # are root-owned; running the backend as that same uid is the
            # most reliable way to read them without manual PUID tuning.
            [ -z "$PUID" ] && PUID="$DETECTED_UID"
            [ -z "$PGID" ] && PGID="$DETECTED_GID"
            echo "[entrypoint] auto-detected media owner: uid=$PUID gid=$PGID"
        fi
    fi
fi

# Final defaults.
PUID="${PUID:-1000}"
PGID="${PGID:-1000}"
echo "[entrypoint] running backend as uid=$PUID gid=$PGID"

# Own the persistent state dir so SQLite/WAL writes succeed. (Skip for
# uid 0 — already root, nothing to chown.)
if [ "$PUID" != "0" ]; then
    chown -R "$PUID:$PGID" /data 2>/dev/null || true
fi

# Expose the resolved ids to supervisord (gosu reads them at run time).
export PUID PGID

exec "$@"
