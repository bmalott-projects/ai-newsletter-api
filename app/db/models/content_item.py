from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ContentItem(Base):
    __tablename__ = "content_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    newsletter_id: Mapped[int] = mapped_column(ForeignKey("newsletters.id"), index=True)

    interest: Mapped[str] = mapped_column(String(200), index=True)
    source_url: Mapped[str] = mapped_column(String(2048), unique=True, index=True)
    summary: Mapped[str] = mapped_column(Text)

    # pgvector column will be added via migrations once pgvector is enabled
    # (keeping MVP setup simple and migration-first)

    newsletter = relationship("Newsletter", back_populates="content_items")

