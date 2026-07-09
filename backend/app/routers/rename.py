"""Rename preview / execute / undo + token cheat sheet."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.core.naming import TOKEN_REFERENCE
from app.db import get_session
from app.models.library import Library
from app.schemas import RenameExecute, RenamePreview, RenameUndo
from app.services import renamer

router = APIRouter(tags=["rename"])


@router.get("/rename/tokens")
def token_cheatsheet():
    """Return the naming-token reference (for the frontend cheat sheet)."""
    return {"tokens": TOKEN_REFERENCE}


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
