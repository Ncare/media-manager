"""Download TMDB images into media folders."""
from __future__ import annotations

from pathlib import Path

import httpx

from app.config import settings


async def download(url: str, dest: Path) -> Path | None:
    if not url:
        return None
    # Same proxy logic as tmdb.py: settings-page proxy wins; otherwise fall back
    # to HTTP_PROXY env vars. Without this, image downloads bypass the proxy and
    # time out when image.tmdb.org is blocked (e.g. NAS behind GFW).
    use_proxy = settings.tmdb_proxy_enabled and settings.tmdb_proxy_url
    client_kwargs: dict = {"timeout": 30, "follow_redirects": True}
    if use_proxy:
        client_kwargs["proxy"] = settings.tmdb_proxy_url
        client_kwargs["trust_env"] = False
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(**client_kwargs) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return None
            dest.write_bytes(r.content)
        return dest
    except Exception:
        return None
