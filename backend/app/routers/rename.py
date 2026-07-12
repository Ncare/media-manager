"""Rename preview / execute / undo + token cheat sheet."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.core.naming import TOKEN_REFERENCE, _build_token_dict
from app.db import get_session
from app.models.library import Library, LibraryType
from app.models.media import Episode, Movie, TvShow
from app.schemas import RenameExecute, RenamePreview, RenameUndo
from app.services import renamer

router = APIRouter(tags=["rename"])


@router.get("/rename/tokens")
def token_cheatsheet():
    """Return the naming-token reference (for the frontend cheat sheet)."""
    return {"tokens": TOKEN_REFERENCE}


@router.get("/rename/token-availability/{library_id}")
def token_availability(
    library_id: int,
    media_type: str = Query("movie", description="movie | tv"),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    """For each template token, report whether it has a value across the media
    in this library. Returns {token: "filled" | "empty"}.

    Used by the template editor to highlight which tokens carry real data so
    the user knows what they can actually rely on. Only movie/tv common tokens
    are reported; TV-only tokens (season/episode/...) are included for tv.
    """
    lib = session.get(Library, library_id)
    if not lib:
        raise HTTPException(404, "library not found")

    # Accumulate: a token is "filled" if ANY media item has it populated.
    filled: set[str] = set()
    considered: set[str] = set()

    def consider(ctx: dict) -> None:
        d = _build_token_dict(ctx)
        for k, v in d.items():
            considered.add(k)
            if v:
                filled.add(k)

    if media_type == "tv" or lib.type == LibraryType.tv:
        for row in session.exec(select(TvShow).where(TvShow.library_id == library_id)).all():
            consider({"title": row.title, "original_title": row.original_title,
                      "year": row.year, "tmdb_id": row.tmdb_id, "imdb_id": row.imdb_id,
                      "rating": row.rating, "votes": row.votes, "genres": row.genres,
                      "certification": row.certification, "runtime": row.runtime,
                      "studio": row.studio, "collection": row.collection,
                      "language": row.language, "show_title": row.title})
        # episodes carry season/episode + technical fields
        for row in session.exec(select(Episode).where(Episode.show_id.in_(
            select(TvShow.id).where(TvShow.library_id == library_id)
        ))).all():
            consider({"season_number": row.season_number, "episode_number": row.episode_number,
                      "title": row.title, "resolution": row.resolution, "source": row.source,
                      "codec": row.codec, "filename": row.file_path})
    else:
        for row in session.exec(select(Movie).where(Movie.library_id == library_id)).all():
            consider({"title": row.title, "parsed_title": row.parsed_title,
                      "original_title": row.original_title, "year": row.year,
                      "parsed_year": row.parsed_year, "tmdb_id": row.tmdb_id,
                      "imdb_id": row.imdb_id, "rating": row.rating, "votes": row.votes,
                      "genres": row.genres, "certification": row.certification,
                      "runtime": row.runtime, "studio": row.studio,
                      "collection": row.collection, "language": row.language,
                      "resolution": row.resolution, "source": row.source,
                      "codec": row.codec, "audio_codec": row.audio_codec,
                      "audio_channels": row.audio_channels,
                      "release_group": row.release_group, "filename": row.file_path})

    return {tok: ("filled" if tok in filled else "empty") for tok in sorted(considered)}


@router.get("/rename/preview/{library_id}", response_model=RenamePreview)
def preview(
    library_id: int,
    template: str | None = Query(None, description="Optional template override"),
    session: Session = Depends(get_session),
):
    lib = session.get(Library, library_id)
    if not lib:
        raise HTTPException(404, "library not found")
    items = (
        renamer.preview_movies(session, lib, template)
        if lib.type.value == "movie"
        else renamer.preview_episodes(session, lib, template)
    )
    return RenamePreview(items=items)


@router.post("/rename/execute")
def execute(payload: RenameExecute, session: Session = Depends(get_session)):
    lib = session.get(Library, payload.library_id)
    if not lib:
        raise HTTPException(404, "library not found")
    batch_id, moved = renamer.execute(
        session, lib, payload.items, payload.media_type, payload.template
    )
    return {"batch_id": batch_id, "moved": moved}


@router.post("/rename/undo")
def undo(payload: RenameUndo, session: Session = Depends(get_session)):
    reverted = renamer.undo(session, payload.batch_id)
    return {"reverted": reverted}
