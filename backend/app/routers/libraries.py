"""Library CRUD + scan trigger."""
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.config import settings
from app.core.naming import DEFAULT_MOVIE_TEMPLATE, DEFAULT_TV_EPISODE_TEMPLATE
from app.db import get_session
from app.models.library import Library, LibraryType
from app.models.media import Episode, Movie, TvShow
from app.schemas import LibraryCreate, LibraryRead, LibraryUpdate
from app.services import tasks

router = APIRouter(prefix="/libraries", tags=["libraries"])


def _to_read(s: Session, lib: Library) -> LibraryRead:
    movie_count = s.exec(select(Movie).where(Movie.library_id == lib.id)).all().__len__()
    tv_count = s.exec(select(TvShow).where(TvShow.library_id == lib.id)).all().__len__()
    return LibraryRead(
        id=lib.id, name=lib.name, type=lib.type, root_path=lib.root_path,
        scraper_source=lib.scraper_source, naming_template=lib.naming_template,
        tv_show_template=lib.tv_show_template,
        auto_scrape=lib.auto_scrape, created_at=lib.created_at, updated_at=lib.updated_at,
        movie_count=movie_count, tv_count=tv_count,
    )


@router.get("", response_model=list[LibraryRead])
def list_libraries(session: Session = Depends(get_session)):
    libs = session.exec(select(Library).order_by(Library.name)).all()
    return [_to_read(session, l) for l in libs]


@router.post("", response_model=LibraryRead, status_code=201)
def create_library(payload: LibraryCreate, session: Session = Depends(get_session)):
    data = payload.model_dump()
    # A TV library should use the episode template by default; if the caller
    # didn't override naming_template it still carries the movie default, so fix it.
    if data.get("type") == LibraryType.tv and data.get("naming_template") == DEFAULT_MOVIE_TEMPLATE:
        data["naming_template"] = DEFAULT_TV_EPISODE_TEMPLATE
    lib = Library(**data)
    session.add(lib)
    session.commit()
    session.refresh(lib)
    return _to_read(session, lib)


@router.patch("/{library_id}", response_model=LibraryRead)
def update_library(library_id: int, payload: LibraryUpdate, session: Session = Depends(get_session)):
    lib = session.get(Library, library_id)
    if not lib:
        raise HTTPException(404, "library not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(lib, k, v)
    lib.updated_at = datetime.utcnow()
    session.add(lib)
    session.commit()
    session.refresh(lib)
    return _to_read(session, lib)


@router.delete("/{library_id}", status_code=204)
def delete_library(library_id: int, session: Session = Depends(get_session)):
    lib = session.get(Library, library_id)
    if not lib:
        raise HTTPException(404, "library not found")
    session.delete(lib)
    session.commit()


@router.post("/{library_id}/scan")
def trigger_scan(library_id: int, session: Session = Depends(get_session)):
    lib = session.get(Library, library_id)
    if not lib:
        raise HTTPException(404, "library not found")
    task = tasks.run_scan(library_id)
    return {"task_id": task.id, "status": task.status}


@router.get("/browse")
def browse_dirs(path: str | None = Query(default=None)) -> list[dict]:
    """List subdirectories under the media root for the directory picker.

    `path` is relative to MEDIA_ROOT (e.g. "Movies" or "Movies/Action");
    omitted/empty → list MEDIA_ROOT itself. Only directories are returned
    (files are hidden), and a path-traversal guard keeps the result inside
    MEDIA_ROOT so callers can't escape the mounted media tree.
    """
    root: Path = settings.media_root.resolve()
    if path:
        # relative segments only — reject anything that tries to go up
        target = (root / path).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            raise HTTPException(400, "path outside media root")
    else:
        target = root

    if not target.is_dir():
        raise HTTPException(404, "directory not found")

    out = []
    try:
        for entry in sorted(target.iterdir(), key=lambda p: p.name.lower()):
            if entry.is_dir():
                out.append({
                    "name": entry.name,
                    "path": str(entry.relative_to(root)),
                })
    except PermissionError:
        raise HTTPException(
            403,
            "无权读取该目录。请检查容器内后端进程的 uid 是否有权限访问挂载的媒体目录；"
            "可在 compose 里设置 PUID/PGID 匹配目录属主，或确认目录对其他用户可读。",
        )
    return out
