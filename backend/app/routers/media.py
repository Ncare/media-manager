"""Movie / TvShow / Episode list + detail reads."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, func, select

from app.db import get_session
from app.models.media import Episode, Movie, Season, TvShow
from app.schemas import EpisodeRead, MovieRead, TvShowRead

router = APIRouter(tags=["media"])


@router.get("/movies", response_model=list[MovieRead])
def list_movies(
    library_id: int | None = None,
    scraped: bool | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
    session: Session = Depends(get_session),
):
    stmt = select(Movie)
    if library_id is not None:
        stmt = stmt.where(Movie.library_id == library_id)
    if scraped is not None:
        stmt = stmt.where(Movie.scraped == scraped)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(Movie.title.like(like) | Movie.parsed_title.like(like))
    stmt = stmt.order_by(Movie.title).offset((page - 1) * size).limit(size)
    return list(session.exec(stmt).all())


@router.get("/movies/{movie_id}", response_model=MovieRead)
def get_movie(movie_id: int, session: Session = Depends(get_session)):
    m = session.get(Movie, movie_id)
    if not m:
        raise HTTPException(404, "movie not found")
    return m


@router.get("/tv", response_model=list[TvShowRead])
def list_tv(
    library_id: int | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
    session: Session = Depends(get_session),
):
    stmt = select(TvShow)
    if library_id is not None:
        stmt = stmt.where(TvShow.library_id == library_id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(TvShow.title.like(like) | TvShow.parsed_title.like(like))
    stmt = stmt.order_by(TvShow.title).offset((page - 1) * size).limit(size)
    shows = list(session.exec(stmt).all())
    out: list[TvShowRead] = []
    for s in shows:
        seasons = session.exec(select(Season).where(Season.show_id == s.id)).all()
        episodes = session.exec(select(Episode).where(Episode.show_id == s.id)).all()
        out.append(TvShowRead(
            **s.model_dump(),
            season_count=len(seasons),
            episode_count=len(episodes),
        ))
    return out


@router.get("/tv/{show_id}", response_model=TvShowRead)
def get_tv(show_id: int, session: Session = Depends(get_session)):
    s = session.get(TvShow, show_id)
    if not s:
        raise HTTPException(404, "show not found")
    seasons = session.exec(select(Season).where(Season.show_id == s.id)).all()
    episodes = session.exec(select(Episode).where(Episode.show_id == s.id)).all()
    return TvShowRead(**s.model_dump(), season_count=len(seasons), episode_count=len(episodes))


@router.get("/tv/{show_id}/seasons/{season_number}/episodes", response_model=list[EpisodeRead])
def list_episodes(show_id: int, season_number: int, session: Session = Depends(get_session)):
    return list(session.exec(
        select(Episode).where(Episode.show_id == show_id, Episode.season_number == season_number)
        .order_by(Episode.episode_number)
    ).all())
