"""Directory scanner — walks a library root and upserts Movie / TvShow / Episode rows.

Movie convention: each file (or each immediate folder) is one movie.
TV convention:   library root contains show folders; each folder holds season/episode files.
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from sqlmodel import Session, select

from app.config import settings
from app.models.library import Library, LibraryType
from app.models.media import Episode, Movie, Season, TvShow
from app.services import probe

VIDEO_EXTS = {
    ".mkv", ".mp4", ".avi", ".ts", ".m2ts", ".mov", ".wmv", ".flv",
    ".webm", ".mpg", ".mpeg", ".m4v", ".iso", ".vob", ".3gp",
}
# Files/folders to ignore while scanning.
IGNORE_NAMES = {".DS_Store", "Thumbs.db", ".gitignore", "@eaDir", "@Recycle", "#recycle"}


def _resolve_root(library: Library) -> Path:
    root = Path(library.root_path)
    if not root.is_absolute():
        root = settings.media_root / root
    return root


def _guess(filename: str) -> dict:
    """Parse a filename with guessit; tolerate failures."""
    try:
        from guessit import guessit
        return dict(guessit(filename))
    except Exception:
        return {}


def _str_field(v) -> str | None:
    return str(v) if v not in (None, "") else None


def _int_field(v) -> int | None:
    if v in (None, ""):
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _list_to_str(v) -> str | None:
    """guessit may return lists for some keys; join them."""
    if v in (None, ""):
        return None
    if isinstance(v, (list, tuple)):
        parts = [str(x) for x in v if x not in (None, "")]
        return ", ".join(parts) if parts else None
    return str(v)


def _technical_fields(info: dict, path: Path | None = None) -> dict:
    """Extract normalized technical fields.

    Priority: ffprobe (reads the actual file) > guessit (parses the filename).
    ffprobe gives authoritative codec/resolution/audio but not source/release
    group (those only exist in filenames), so we merge: probe wins where it has
    a value, guessit fills the gaps.
    """
    # --- guessit baseline (from filename) ---
    resolution = _str_field(info.get("screen_size"))
    source = _list_to_str(info.get("source") or info.get("format"))
    codec = _list_to_str(info.get("video_codec") or info.get("video_encoder"))
    audio_codec = _list_to_str(info.get("audio_codec"))
    audio_channels = _list_to_str(info.get("audio_channels"))
    group = _str_field(info.get("release_group"))

    # --- ffprobe override (from file internals) ---
    if path is not None:
        probed = probe.probe(path)
        # probe is authoritative for codec/resolution/audio when available
        codec = probed.get("codec") or codec
        resolution = probed.get("resolution") or resolution
        audio_codec = probed.get("audio_codec") or audio_codec
        audio_channels = probed.get("audio_channels") or audio_channels

    return {
        "resolution": resolution,
        "source": source,
        "codec": codec,
        "audio_codec": audio_codec,
        "audio_channels": audio_channels,
        "release_group": group,
    }


def _is_video(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in VIDEO_EXTS


def _clean(root: Path) -> tuple[set[str], set[str]]:
    """Return (existing_movie_paths, existing_episode_paths) for stale detection."""
    return set(), set()


def scan_library(session: Session, library: Library) -> dict:
    """Scan one library, upserting rows. Returns a summary dict."""
    root = _resolve_root(library)
    if not root.exists():
        return {"added": 0, "updated": 0, "skipped": 0, "error": f"path not found: {root}"}

    added = updated = skipped = 0

    if library.type == LibraryType.movie:
        added, updated, skipped = _scan_movies(session, library, root)
    else:
        added, updated, skipped = _scan_tv(session, library, root)

    library.updated_at = datetime.utcnow()
    session.add(library)
    session.commit()
    return {"added": added, "updated": updated, "skipped": skipped}


def _scan_movies(session: Session, library: Library, root: Path) -> tuple[int, int, int]:
    added = updated = skipped = 0

    # Existing file_path -> Movie lookup for upsert.
    existing = {m.file_path: m for m in session.exec(select(Movie).where(Movie.library_id == library.id))}

    def _process_file(path: Path):
        nonlocal added, updated
        info = _guess(path.stem)
        tech = _technical_fields(info, path)
        movie = existing.get(str(path))
        if movie:
            movie.filename = path.name
            movie.parsed_title = _str_field(info.get("title")) or movie.parsed_title
            movie.parsed_year = _int_field(info.get("year")) or movie.parsed_year
            for k, v in tech.items():
                if v:
                    setattr(movie, k, v or getattr(movie, k, None))
            movie.updated_at = datetime.utcnow()
            session.add(movie)
            updated += 1
        else:
            kwargs = dict(
                library_id=library.id,
                file_path=str(path),
                filename=path.name,
                parsed_title=_str_field(info.get("title")),
                parsed_year=_int_field(info.get("year")),
            )
            kwargs.update({k: v for k, v in tech.items() if v})
            session.add(Movie(**kwargs))
            added += 1

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_NAMES]
        for fn in filenames:
            if fn in IGNORE_NAMES:
                continue
            p = Path(dirpath) / fn
            if _is_video(p):
                _process_file(p)
            else:
                skipped += 1

    session.commit()
    return added, updated, skipped


def _scan_tv(session: Session, library: Library, root: Path) -> tuple[int, int, int]:
    added = updated = skipped = 0
    shows_existing = {s.folder_path: s for s in session.exec(select(TvShow).where(TvShow.library_id == library.id))}

    for show_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        if show_dir.name in IGNORE_NAMES:
            continue
        info = _guess(show_dir.name)
        show = shows_existing.get(str(show_dir))
        if not show:
            show = TvShow(
                library_id=library.id,
                folder_path=str(show_dir),
                parsed_title=_str_field(info.get("title")),
                parsed_year=_int_field(info.get("year")),
            )
            session.add(show)
            session.flush()
            shows_existing[str(show_dir)] = show
            added += 1
        else:
            updated += 1

        a, u, s = _scan_episodes(session, library, show, show_dir)
        added += a
        updated += u
        skipped += s

    session.commit()
    return added, updated, skipped


def _scan_episodes(session: Session, library: Library, show: TvShow, show_dir: Path) -> tuple[int, int, int]:
    added = updated = skipped = 0
    existing = {e.file_path: e for e in session.exec(select(Episode).where(Episode.show_id == show.id))}

    for dirpath, dirnames, filenames in os.walk(show_dir):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_NAMES]
        for fn in filenames:
            if fn in IGNORE_NAMES:
                continue
            p = Path(dirpath) / fn
            if not _is_video(p):
                skipped += 1
                continue
            info = _guess(p.name)
            season_num = _int_field(info.get("season"))
            episode_num = _int_field(info.get("episode"))
            tech = _technical_fields(info, p)

            # Ensure a Season row exists.
            season_id = None
            if season_num is not None:
                season = session.exec(
                    select(Season).where(Season.show_id == show.id, Season.season_number == season_num)
                ).first()
                if not season:
                    season = Season(show_id=show.id, season_number=season_num)
                    session.add(season)
                    session.flush()
                season_id = season.id

            ep = existing.get(str(p))
            if ep:
                ep.filename = p.name
                ep.season_id = season_id or ep.season_id
                ep.season_number = season_num or ep.season_number
                ep.episode_number = episode_num or ep.episode_number
                for k, v in tech.items():
                    if v:
                        setattr(ep, k, v or getattr(ep, k, None))
                ep.parsed_title = _str_field(info.get("title")) or ep.parsed_title
                ep.updated_at = datetime.utcnow()
                session.add(ep)
                updated += 1
            else:
                kwargs = dict(
                    library_id=library.id,
                    show_id=show.id,
                    season_id=season_id,
                    file_path=str(p),
                    filename=p.name,
                    parsed_title=_str_field(info.get("title")),
                    season_number=season_num,
                    episode_number=episode_num,
                )
                kwargs.update({k: v for k, v in tech.items() if v})
                session.add(Episode(**kwargs))
                added += 1

    session.commit()
    return added, updated, skipped
