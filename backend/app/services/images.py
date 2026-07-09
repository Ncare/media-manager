"""Download TMDB images into media folders."""
from __future__ import annotations

from pathlib import Path

import httpx


async def download(url: str, dest: Path) -> Path | None:
    if not url:
        return None
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return None
            dest.write_bytes(r.content)
        return dest
    except Exception:
        return None
