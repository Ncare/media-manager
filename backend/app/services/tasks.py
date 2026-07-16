"""Background task tracking + runners for scan / scrape."""
from __future__ import annotations

import asyncio
import threading
from datetime import datetime

from sqlmodel import Session, select

from app.db import engine
from app.models.library import Library, LibraryType
from app.models.task import Task, TaskStatus, TaskType
from app.services import scanner, scraper


def _new_session() -> Session:
    return Session(engine)


def create_task(library_id: int | None, task_type: TaskType, total: int = 0) -> Task:
    with _new_session() as s:
        task = Task(library_id=library_id, type=task_type, total=total, status=TaskStatus.pending)
        s.add(task)
        s.commit()
        s.refresh(task)
        return task


def _update(task_id: int, **fields) -> None:
    with _new_session() as s:
        task = s.get(Task, task_id)
        if not task:
            return
        for k, v in fields.items():
            setattr(task, k, v)
        task.updated_at = datetime.utcnow()
        s.add(task)
        s.commit()


def run_scan(library_id: int) -> Task:
    """Create a task and kick off scanning in a background thread."""
    task = create_task(library_id, TaskType.scan)
    thread = threading.Thread(target=_scan_worker, args=(task.id, library_id), daemon=True)
    thread.start()
    return task


def _scan_worker(task_id: int, library_id: int) -> None:
    _update(task_id, status=TaskStatus.running, message="scanning")
    try:
        with _new_session() as s:
            library = s.get(Library, library_id)
            if not library:
                _update(task_id, status=TaskStatus.failed, message="library not found")
                return
            result = scanner.scan_library(s, library)
        msg = f"added {result.get('added',0)}, updated {result.get('updated',0)}, removed {result.get('removed',0)}"
        _update(task_id, status=TaskStatus.completed, total=result.get("added", 0) + result.get("updated", 0), done=result.get("added", 0), message=msg)

        # Auto-scrape if enabled.
        with _new_session() as s:
            library = s.get(Library, library_id)
            if library and library.auto_scrape:
                mt = "movie" if library.type == LibraryType.movie else "tv"
                asyncio.run(scraper.auto_scrape_unscraped(s, library_id, mt))
    except Exception as e:  # pragma: no cover
        _update(task_id, status=TaskStatus.failed, message=str(e))


def get_task(task_id: int) -> Task | None:
    with _new_session() as s:
        return s.get(Task, task_id)


def list_recent_tasks(limit: int = 20) -> list[Task]:
    with _new_session() as s:
        return list(s.exec(select(Task).order_by(Task.created_at.desc()).limit(limit)).all())
