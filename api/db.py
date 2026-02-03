"""Database models and session for settings storage."""
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import Boolean, DateTime, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./data/settings.db",
)
if DATABASE_URL.startswith("sqlite"):
    _engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    _engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


class Base(DeclarativeBase):
    pass


CONNECTION_STATUS_SUCCESS = "success"
CONNECTION_STATUS_FAILED = "failed"
CONNECTION_STATUS_NOT_CONFIGURED = "not_configured"


class TelegramSettingsModel(Base):
    __tablename__ = "telegram_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    access_token_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    base_url: Mapped[str] = mapped_column(String(512), nullable=False, default="https://api.telegram.org")
    connection_status: Mapped[str] = mapped_column(String(32), nullable=False, default=CONNECTION_STATUS_NOT_CONFIGURED)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_checked: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LLMSettingsModel(Base):
    __tablename__ = "llm_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    llm_type: Mapped[str] = mapped_column(String(64), nullable=False)
    api_key_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    base_url: Mapped[str] = mapped_column(String(512), nullable=False)
    model_type: Mapped[str] = mapped_column(String(128), nullable=False)
    system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    connection_status: Mapped[str] = mapped_column(String(32), nullable=False, default=CONNECTION_STATUS_NOT_CONFIGURED)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_checked: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def init_db() -> None:
    """Create tables if they do not exist. For SQLite, ensure data dir exists."""
    if DATABASE_URL.startswith("sqlite"):
        path = DATABASE_URL.replace("sqlite:///", "").strip()
        if path.startswith("./"):
            Path(path).parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=_engine)
    logger.debug("Database tables created or already exist")
