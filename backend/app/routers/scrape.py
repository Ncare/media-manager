"""Scrape endpoints — TMDB search, manual match, bulk scrape."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.db import get_session
from app.models.media import Episode, Movie, TvShow
from app.schemas import ManualMatch, TmdbSearchResult
from app.services import scraper
from app.services.tmdb import TMDBClient, TMDBError

logger = logging.getLogger(__name__)
router = APIRouter(tags=["scrape"])


@router.get("/search", response_model=list[TmdbSearchResult])
async def search(q: str, media_type: str = "movie", year: int | None = None):
    client = TMDBClient()
    if not client.configured:
        raise HTTPException(400, "未配置 TMDB API Key,请先到「设置」页填写")
    try:
        return await scraper.search_tmdb(client, q, media_type=media_type, year=year)
    except TMDBError as e:
        raise HTTPException(502, str(e))
    except Exception as e:
        logger.exception("TMDB search failed unexpectedly")
        raise HTTPException(502, f"搜索失败:{e}")


@router.post("/match")
async def manual_match(payload: ManualMatch, session: Session = Depends(get_session)):
    """Force-match a media item to a specific TMDB id and scrape it."""
    client = TMDBClient()
    if not client.configured:
        raise HTTPException(400, "未配置 TMDB API Key,请先到「设置」页填写")
    try:
        if payload.media_type == "movie":
            item = session.get(Movie, payload.media_id)
            if not item:
                raise HTTPException(404, "电影不存在")
            await scraper.scrape_movie(session, item, payload.tmdb_id)
        elif payload.media_type == "tv":
            item = session.get(TvShow, payload.media_id)
            if not item:
                raise HTTPException(404, "剧集不存在")
            await scraper.scrape_tv(session, item, payload.tmdb_id)
        elif payload.media_type == "episode":
            item = session.get(Episode, payload.media_id)
            show = session.get(TvShow, item.show_id) if item else None
            if not item or not show or not show.tmdb_id:
                raise HTTPException(400, "剧集需先刮削整剧后再匹配单集")
            await scraper.scrape_episode(session, item, show.tmdb_id)
        else:
            raise HTTPException(400, "未知的媒体类型")
    except TMDBError as e:
        raise HTTPException(502, str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Match/scrape failed unexpectedly")
        raise HTTPException(502, f"刮削失败:{e}")
    return {"ok": True}
