"""ORM models. Text columns use LONGTEXT on MySQL (plain TEXT is capped at 64 KB there)."""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base

LongText = Text().with_variant(mysql.LONGTEXT(), "mysql")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(10))
    size_bytes: Mapped[int]
    page_count: Mapped[Optional[int]]
    char_count: Mapped[int]
    word_count: Mapped[int]
    extraction_method: Mapped[str] = mapped_column(String(30))
    extracted_text: Mapped[str] = mapped_column(LongText)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
