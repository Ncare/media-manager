"""Rename undo log — every executed rename is recorded for revert."""
from datetime import datetime

from sqlmodel import Field, SQLModel


class RenameLog(SQLModel, table=True):
    __tablename__ = "rename_log"

    id: int | None = Field(default=None, primary_key=True)
    library_id: int = Field(foreign_key="library.id", index=True)
    batch_id: str = Field(index=True)  # group items from one execute call
    from_path: str
    to_path: str
    media_type: str = "movie"  # movie | episode
    media_id: int | None = None
    reversed: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    # JSON list of [from, to] pairs for companion files (poster.jpg, fanart.jpg,
    # *.nfo, season posters) moved alongside the media file. Stored as a string
    # for SQLite simplicity; empty/null when none were moved.
    companion_paths: str | None = None
