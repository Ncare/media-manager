"""Renamer — dry-run preview, execute (with undo log), and undo.

Templates use the token engine in app.core.naming, e.g.::

    Movie:  {title} ({year})/{titleSort;originalTitle;title} ({year}) [{resolution};{source}]{ext}
    TV ep:  {showTitle}/Season {season}/{showTitle} - {seasonEpisode} - {title}{ext}
    TV show folder: {showTitle} ({year})

Fallback syntax ``{originalTitle;title}`` picks the first non-empty token.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime
from pathlib import Path

from sqlmodel import Session, select

from app.core.naming import apply_template
from app.models.library import Library, LibraryType
from app.models.media import Episode, Movie, TvShow
from app.models.rename_log import RenameLog
from app.schemas import RenamePreviewItem


def _row_context(row, *, show: TvShow | None = None, ext: str | None = None) -> dict:
    """Build a flat context dict for the naming engine from a media row."""
    ctx = {k: getattr(row, k, None) for k in (
        "title", "original_title", "year", "tmdb_id", "imdb_id", "rating", "votes",
        "genres", "certification", "runtime", "studio", "collection", "language",
        "resolution", "source", "codec", "audio_codec", "audio_channels",
        "release_group", "parsed_title", "parsed_year",
    )}
    # normalize a couple aliases the engine also accepts
    ctx["ext"] = ext
    if show is not None:
        ctx["show_title"] = show.title or show.original_title or show.parsed_title
        # episodes may want the show's year/ids if their own are empty
        ctx.setdefault("year", row.year or show.year)
    # season/episode for episodes
    ctx["season"] = getattr(row, "season_number", None)
    ctx["episode"] = getattr(row, "episode_number", None)
    return ctx


def _split_rel(template: str) -> str:
    """Everything after the last '/' is the filename portion."""
    return template


def _template_has_dir(template: str) -> bool:
    return "/" in template


def preview_movies(session: Session, library: Library, template: str | None = None) -> list[RenamePreviewItem]:
    template = template or library.naming_template
    movies = session.exec(select(Movie).where(Movie.library_id == library.id)).all()
    items: list[RenamePreviewItem] = []
    for m in movies:
        src = Path(m.file_path)
        if not src.exists():
            continue
        ctx = _row_context(m, ext=src.suffix)
        target_rel = apply_template(template, ctx)
        dest = _resolve_movie_dest(src, target_rel)
        conflict = dest.exists() and dest.resolve() != src.resolve()
        items.append(RenamePreviewItem(
            media_id=m.id, media_type="movie",
            from_path=str(src), to_path=str(dest), conflict=conflict,
        ))
    return items


def preview_episodes(session: Session, library: Library, template: str | None = None) -> list[RenamePreviewItem]:
    template = template or library.naming_template
    episodes = session.exec(select(Episode).where(Episode.library_id == library.id)).all()
    items: list[RenamePreviewItem] = []
    for ep in episodes:
        src = Path(ep.file_path)
        if not src.exists():
            continue
        show = session.get(TvShow, ep.show_id)
        ctx = _row_context(ep, show=show, ext=src.suffix)
        target_rel = apply_template(template, ctx)
        dest = _resolve_episode_dest(src, target_rel, show, ep.season_number)
        conflict = dest.exists() and dest.resolve() != src.resolve()
        items.append(RenamePreviewItem(
            media_id=ep.id, media_type="episode",
            from_path=str(src), to_path=str(dest), conflict=conflict,
        ))
    return items


def _resolve_movie_dest(src: Path, target_rel: str) -> Path:
    """Compute the destination for a movie file.

    If the template contains a '/', the leading segment(s) define a subfolder
    *under the existing movie's own folder* (not the library root), so files
    stay grouped. Without '/', the file just changes its name in place.
    """
    if _template_has_dir(target_rel):
        # Keep within the movie's folder (its parent) — group artwork + nfo together.
        return src.parent / target_rel
    return src.parent / target_rel


def _resolve_episode_dest(src: Path, target_rel: str, show: TvShow | None, season_num) -> Path:
    """For episodes, the template usually starts with {showTitle}.

    We anchor relative to the SHOW folder so the season structure is rebuilt.
    The first path segment is expected to be the show folder name.
    """
    parts = Path(target_rel).parts
    if len(parts) >= 2:
        # show_folder / [Season x /] filename
        show_folder = src.parent
        # walk up to the show folder: src is typically .../Show/Season 01/ep
        # detect by matching the show's stored folder_path.
        if show is not None:
            try:
                sp = Path(show.folder_path)
                show_folder = sp
            except Exception:
                pass
        return show_folder / Path(*parts[1:]) if len(parts) > 1 else show_folder / target_rel
    return src.parent / target_rel


def execute(
    session: Session,
    library: Library,
    media_ids: list[int],
    media_type: str,
    template: str | None = None,
) -> tuple[str, int]:
    """Execute rename for selected ids. Returns (batch_id, count_moved)."""
    batch_id = uuid.uuid4().hex[:12]
    moved = 0

    previews = (
        preview_movies(session, library, template)
        if media_type == "movie"
        else preview_episodes(session, library, template)
    )
    by_media = {p.media_id: p for p in previews}

    for mid in media_ids:
        plan = by_media.get(mid)
        if not plan:
            continue
        src = Path(plan.from_path)
        dest = Path(plan.to_path)
        if not src.exists() or dest.exists():
            continue
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            os.rename(src, dest)
        except OSError:
            continue

        # Keep the DB row's stored path valid.
        if media_type == "movie":
            row = session.get(Movie, mid)
        else:
            row = session.get(Episode, mid)
        if row is not None:
            row.file_path = str(dest)
            row.filename = dest.name
            row.updated_at = datetime.utcnow()
            session.add(row)

        session.add(RenameLog(
            library_id=library.id, batch_id=batch_id,
            from_path=plan.from_path, to_path=plan.to_path,
            media_type=media_type, media_id=mid,
        ))
        moved += 1

    session.commit()
    return batch_id, moved


def undo(session: Session, batch_id: str | None = None) -> int:
    """Revert a rename batch (latest if batch_id is None). Returns count reverted."""
    if batch_id is None:
        latest = session.exec(
            select(RenameLog).where(RenameLog.reversed == False).order_by(RenameLog.created_at.desc())
        ).first()
        if not latest:
            return 0
        batch_id = latest.batch_id

    logs = session.exec(select(RenameLog).where(RenameLog.batch_id == batch_id, RenameLog.reversed == False)).all()
    reverted = 0
    # reverse the move, and patch DB paths back.
    for log in logs:
        src = Path(log.to_path)
        dest = Path(log.from_path)
        moved_back = False
        try:
            if src.exists() and not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                os.rename(src, dest)
                moved_back = True
                reverted += 1
        except OSError:
            moved_back = False
        finally:
            if moved_back:
                _restore_db_path(session, log)
            log.reversed = True
            session.add(log)
    session.commit()
    return reverted


def _restore_db_path(session: Session, log: RenameLog) -> None:
    """Point the media row back to its original path after undo."""
    Model = Movie if log.media_type == "movie" else Episode
    if log.media_id is None:
        return
    row = session.get(Model, log.media_id)
    if row is not None:
        row.file_path = log.from_path
        row.filename = Path(log.from_path).name
        session.add(row)
