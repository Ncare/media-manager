"""Scrape endpoints — TMDB search, manual match, bulk scrape."""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models.media import Episode, Movie, TvShow
from app.schemas import ManualMatch, TmdbSearchResult
from app.services import scraper
from app.services.tmdb import TMDBClient, TMDBError

router = APIRouter(tags=["scrape"])


@router.get("/search", response_model=list[TmdbSearchResult])
async def search(q: str, media_type: str = "movie", year: int | None = None):
    client = TMDBClient()
    if not client.configured:
        raise HTTPException(400, "TMDB API key not configured. Set TMDB_API_KEY in Settings.")
    try:
        return await scraper.search_tmdb(client, q, media_type=media_type, year=year)
    except TMDBError as e:
        raise HTTPException(502, str(e))


@router.post("/match")
async def manual_match(payload: ManualMatch, session: Session = Depends(get_session)):
    """Force-match a media item to a specific TMDB id and scrape it."""
    client = TMDBClient()
    if not client.configured:
        raise HTTPException(400, "TMDB API key not configured")
    try:
        if payload.media_type == "movie":
            item = session.get(Movie, payload.media_id)
            if not item:
                raise HTTPException(404, "movie not found")
            await scraper.scrape_movie(session, item, payload.tmdb_id)
        elif payload.media_type == "tv":
            item = session.get(TvShow, payload.media_id)
            if not item:
                raise HTTPException(404, "show not found")
            await scraper.scrape_tv(session, item, payload.tmdb_id)
        elif payload.media_type == "episode":
            item = session.get(Episode, payload.media_id)
            show = session.get(TvShow, item.show_id) if item else None
            if not item or not show or not show.tmdb_id:
                raise HTTPException(400, "episode requires a scraped show first")
            await scraper.scrape_episode(session, item, show.tmdb_id)
        else:
            raise HTTPException(400, "unknown media_type")
    except TMDBError as e:
        raise HTTPException(502, str(e))
    return {"ok": True}
