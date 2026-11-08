"""SQLAlchemy ORM models for the Quran recitation backend."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    recitations: Mapped[List["Recitation"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    progress: Mapped[List["Progress"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User(id={self.id}, username={self.username!r})>"


class Recitation(Base):
    __tablename__ = "recitations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    surah_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    ayah_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    audio_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    transcribed_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    corrected_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tajweed_errors: Mapped[Optional[List[dict]]] = mapped_column(JSON, nullable=True)  # JSON list of detected errors
    confidence_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="recitations")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Recitation(id={self.id}, surah={self.surah_number}, ayah={self.ayah_number})>"


class Progress(Base):
    __tablename__ = "progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    surah_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    ayah_number: Mapped[int] = mapped_column(Integer, nullable=False)
    last_recited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    recitation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tajweed_error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="progress")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Progress(user={self.user_id}, surah={self.surah_number}, ayah={self.ayah_number})>"
