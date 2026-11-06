from datetime import datetime, timezone
from enum import Enum
from sqlmodel import Field, SQLModel


class Status(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"


class Files(SQLModel, table=True):
    __tablename__ = "files"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    size: int
    object_key: str = Field(index=True)
    status: Status = Field(default=Status.completed)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Alias for singular import compatibility
File = Files


class UploadSession(SQLModel, table=True):
    __tablename__ = "upload_sessions"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    file_size: int
    object_key: str = Field(index=True)
    upload_id: str | None = Field(default=None, nullable=True)
    total_parts: int | None = Field(default=None, nullable=True)
    status: Status = Field(default=Status.pending)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
