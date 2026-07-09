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
