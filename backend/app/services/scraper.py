"""Scraper — match files to TMDB, persist metadata, and trigger image downloads."""
from __future__ import annotations

import asyncio
from datetime import datetime

from sqlmodel import Session, select

from app.models.media import Episode, Movie, Season, TvShow
from app.schemas import TmdbSearchResult
from app.services import images, nfo
from app.services.tmdb import TMDBClient, image_url


def _pick_title_year(item):
    """Extract a title + year guess from a movie/episode/show for searching."""
    title = item.title or item.parsed_title
    year = item.year or item.parsed_year
    return title, year


async def search_tmdb(client: TMDBClient, query: str, media_type: str, year: int | None = None) -> list[TmdbSearchResult]:
    raw = await client.search(query, media_type=media_type, year=year)
    results: list[TmdbSearchResult] = []
    for r in raw:
        title = r.get("title") or r.get("name") or ""
        original = r.get("original_title") or r.get("original_name")
        date = r.get("release_date") or r.get("first_air_date") or ""
        year_val = int(date[:4]) if len(date) >= 4 and date[:4].isdigit() else None
        poster = image_url(r.get("poster_path"))
        backdrop = image_url(r.get("backdrop_path"), "w1280")
        results.append(TmdbSearchResult(
            tmdb_id=r.get("id"),
            title=title,
            original_title=original,
            year=year_val,
            overview=r.get("overview"),
            poster_url=poster,
            backdrop_url=backdrop,
        ))
    return results


def _apply_common(item, data: dict) -> None:
    """Copy shared TMDB fields onto a movie/show model."""
    genres = data.get("genres") or []
    item.title = data.get("title") or data.get("name") or item.title
    item.original_title = data.get("original_title") or data.get("original_name") or item.original_title
    date = data.get("release_date") or data.get("first_air_date") or ""
    if len(date) >= 4 and date[:4].isdigit():
        item.year = int(date[:4])
    item.overview = data.get("overview")
    item.rating = data.get("vote_average")
    item.votes = data.get("vote_count")
    item.runtime = _first_int(data.get("runtime") or data.get("episode_run_time"))
    item.certification = _certification(data)
    item.genres = ", ".join(g.get("name", "") for g in genres) or None
    item.language = data.get("original_language")
    studios = data.get("production_companies") or []
    item.studio = ", ".join(s.get("name", "") for s in studios) or None
    coll = data.get("belongs_to_collection") or {}
    item.collection = coll.get("name") if isinstance(coll, dict) else None
    item.imdb_id = data.get("imdb_id") or item.imdb_id
    item.poster_path = image_url(data.get("poster_path"), "original")
    item.backdrop_path = image_url(data.get("backdrop_path"), "original")
    item.scraped = True
    item.updated_at = datetime.utcnow()


def _first_int(v) -> int | None:
    if v in (None, ""):
        return None
    if isinstance(v, (list, tuple)):
        v = v[0] if v else None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _certification(data: dict) -> str | None:
    """Extract a single certification/rating from TMDB release_dates (movies)."""
    rd = data.get("release_dates") or {}
    results = rd.get("results") or []
    for entry in results:
        for r in entry.get("release_dates") or []:
            cert = r.get("certification")
            if cert:
                return cert
    # TV uses content_ratings
    cr = data.get("content_ratings") or {}
    for entry in cr.get("results") or []:
        rating = entry.get("rating")
        if rating:
            return rating
    return None


async def scrape_movie(session: Session, movie: Movie, tmdb_id: int) -> None:
    client = TMDBClient()
    data = await client.get_movie(tmdb_id)
    _apply_common(movie, data)
    movie.tmdb_id = tmdb_id
    session.add(movie)
    session.commit()

    # Download artwork next to the file; write NFO.
    folder = _parent(movie.file_path)
    if movie.poster_path:
        await images.download(movie.poster_path, folder / "poster.jpg")
    if movie.backdrop_path:
        await images.download(movie.backdrop_path, folder / "fanart.jpg")
    nfo.write_movie_nfo(folder / "movie.nfo", movie)


async def scrape_tv(session: Session, show: TvShow, tmdb_id: int) -> None:
    client = TMDBClient()
    data = await client.get_tv(tmdb_id)
    _apply_common(show, data)
    show.tmdb_id = tmdb_id
    session.add(show)
    session.commit()

    folder = _parent(show.folder_path)
    if show.poster_path:
        await images.download(show.poster_path, folder / "poster.jpg")
    if show.backdrop_path:
        await images.download(show.backdrop_path, folder / "fanart.jpg")
    nfo.write_tvshow_nfo(folder / "tvshow.nfo", show)

    # Upsert seasons and scrape episodes.
    seasons = data.get("seasons", [])
    # Persist known seasons.
    for s in seasons:
        num = s.get("season_number")
        if num is None:
            continue
        season = session.exec(
            select(Season).where(Season.show_id == show.id, Season.season_number == num)
        ).first()
        if not season:
            season = Season(show_id=show.id, season_number=num)
        season.title = s.get("name")
        season.tmdb_id = s.get("id")
        season.poster_path = image_url(s.get("poster_path"), "original")
        session.add(season)
        session.commit()
        if season.poster_path:
            await images.download(season.poster_path, folder / f"season{num:02d}-poster.jpg")

    # Scrape each episode row.
    episodes = session.exec(select(Episode).where(Episode.show_id == show.id)).all()
    for ep in episodes:
        if ep.season_number is not None and ep.episode_number is not None:
            try:
                await scrape_episode(session, ep, tmdb_id)
            except Exception:
                continue  # keep going even if one episode fails


async def scrape_episode(session: Session, ep: Episode, show_tmdb_id: int) -> None:
    client = TMDBClient()
    data = await client.get_episode(show_tmdb_id, ep.season_number, ep.episode_number)
    ep.title = data.get("name")
    ep.overview = data.get("overview")
    ep.tmdb_id = data.get("id")
    ep.poster_path = image_url(data.get("still_path"), "original")
    ep.scraped = True
    ep.updated_at = datetime.utcnow()
    session.add(ep)
    session.commit()
    folder = _parent(ep.file_path)
    nfo.write_episode_nfo(folder / f"{_stem(ep.file_path)}.nfo", ep)


def _parent(path: str):
    from pathlib import Path
    return Path(path).parent


def _stem(path: str):
    from pathlib import Path
    return Path(path).stem


async def auto_scrape_unscraped(session: Session, library_id: int, media_type: str) -> int:
    """Auto-match every unscraped item by its parsed title. Returns count attempted."""
    client = TMDBClient()
    attempted = 0
    if media_type == "movie":
        rows = session.exec(select(Movie).where(Movie.library_id == library_id, Movie.scraped == False)).all()
        for m in rows:
            title, year = _pick_title_year(m)
            if not title:
                continue
            results = await client.search(title, "movie", year=year)
            if results:
                try:
                    await scrape_movie(session, m, results[0]["id"])
                    attempted += 1
                except Exception:
                    continue
    else:
        rows = session.exec(select(TvShow).where(TvShow.library_id == library_id, TvShow.scraped == False)).all()
        for s in rows:
            title, year = _pick_title_year(s)
            if not title:
                continue
            results = await client.search(title, "tv", year=year)
            if results:
                try:
                    await scrape_tv(session, s, results[0]["id"])
                    attempted += 1
                except Exception:
                    continue
    return attempted
