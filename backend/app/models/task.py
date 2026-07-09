"""Background task status (scan / scrape progress)."""
from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel


class TaskStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    canceled = "canceled"


class TaskType(str, Enum):
    scan = "scan"
    scrape = "scrape"
    rename = "rename"


class Task(SQLModel, table=True):
    __tablename__ = "task"

    id: int | None = Field(default=None, primary_key=True)
    library_id: int | None = Field(default=None, index=True)
    type: TaskType = Field(index=True)
    status: TaskStatus = Field(default=TaskStatus.pending, index=True)
    total: int = Field(default=0)
    done: int = Field(default=0)
    message: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
