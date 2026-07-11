"""TMDB API client (async via httpx)."""
from __future__ import annotations

import httpx

from app.config import settings


class TMDBError(Exception):
    """Carries a localized (Chinese) message so it can flow straight to the API
    response. Callers should pass a finished, user-facing string as the message
    rather than relying on default formatting."""
    pass


class TMDBClient:
    def __init__(self, api_key: str | None = None, language: str | None = None):
        self.api_key = api_key if api_key is not None else settings.tmdb_api_key
        self.language = language if language is not None else settings.tmdb_language

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _params(self, extra: dict | None = None) -> dict:
        params = {"api_key": self.api_key, "language": self.language}
        if extra:
            params.update(extra)
        return params

    async def _get(self, path: str, params: dict | None = None) -> dict:
        if not self.configured:
            raise TMDBError("未配置 TMDB API Key,请在「设置」页填入后再搜索")
        url = f"{settings.tmdb_base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.get(url, params=self._params(params))
        except httpx.TimeoutException:
            raise TMDBError("连接 TMDB 超时,请检查 NAS 的网络是否能访问外网(api.themoviedb.org)")
        except httpx.ConnectError:
            raise TMDBError("无法连接 TMDB 服务器,请检查 NAS 的网络连接或 DNS 设置")
        except httpx.HTTPError as e:
            raise TMDBError(f"请求 TMDB 失败:{e}")
        if r.status_code == 401:
            raise TMDBError("TMDB API Key 无效或已过期(401 未授权),请到「设置」页检查 Key 是否正确")
        if r.status_code == 404:
            raise TMDBError("TMDB 上找不到该资源(404)")
        if r.status_code == 429:
            raise TMDBError("TMDB 请求过于频繁,已触发限流(429),请稍后再试")
        if r.status_code != 200:
            # Surface TMDB's own error text so it's diagnosable instead of a
            # bare status code.
            raise TMDBError(f"TMDB 返回错误 {r.status_code}:{r.text[:200]}")
        return r.json()

    async def search(self, query: str, media_type: str = "movie", year: int | None = None) -> list[dict]:
        # /search/tv and /search/movie both exist; /search/multi also available.
        endpoint = "/search/movie" if media_type == "movie" else "/search/tv"
        params: dict = {"query": query, "include_adult": "false"}
        if year:
            params["year" if media_type == "movie" else "first_air_date_year"] = str(year)
        data = await self._get(endpoint, params)
        return data.get("results", [])

    async def get_movie(self, tmdb_id: int) -> dict:
        return await self._get(
            f"/movie/{tmdb_id}",
            {"append_to_response": "credits,images,release_dates,external_ids"},
        )

    async def get_tv(self, tmdb_id: int) -> dict:
        return await self._get(
            f"/tv/{tmdb_id}",
            {"append_to_response": "credits,images,content_ratings,external_ids"},
        )

    async def get_tv_season(self, tmdb_id: int, season_number: int) -> dict:
        return await self._get(f"/tv/{tmdb_id}/season/{season_number}")

    async def get_episode(self, tmdb_id: int, season: int, episode: int) -> dict:
        return await self._get(f"/tv/{tmdb_id}/season/{season}/episode/{episode}")


def image_url(path: str | None, size: str = "w500") -> str | None:
    """Build a full TMDB image URL from a poster/backdrop path."""
    if not path:
        return None
    return f"{settings.tmdb_image_base}/{size}{path}"
