"""Database models and session for settings storage."""
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import BigInteger, Boolean, DateTime, String, Text, create_engine, text
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


class ServiceAdminModel(Base):
    __tablename__ = "service_admins"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    role: Mapped[str] = mapped_column(String(64), nullable=False, default="service_admin")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    profile_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class LLMSettingsModel(Base):
    __tablename__ = "llm_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    llm_type: Mapped[str] = mapped_column(String(64), nullable=False)
    api_key_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    base_url: Mapped[str] = mapped_column(String(512), nullable=False)
    model_type: Mapped[str] = mapped_column(String(128), nullable=False)
    system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    azure_endpoint: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    api_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    project_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    connection_status: Mapped[str] = mapped_column(String(32), nullable=False, default=CONNECTION_STATUS_NOT_CONFIGURED)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_checked: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def _sqlite_migrate_llm_azure_columns() -> None:
    """Add azure_endpoint, api_version, and project_id to llm_settings if missing (SQLite)."""
    if not DATABASE_URL.startswith("sqlite"):
        return
    with _engine.connect() as conn:
        try:
            r = conn.execute(
                text(
                    "SELECT name FROM pragma_table_info('llm_settings') WHERE name IN ('azure_endpoint', 'api_version', 'project_id')"
                )
            )
            existing = {row[0] for row in r}
        except Exception:
            return
        for col, typ in [
            ("azure_endpoint", "VARCHAR(512)"),
            ("api_version", "VARCHAR(64)"),
            ("project_id", "VARCHAR(128)"),
        ]:
            if col not in existing:
                try:
                    conn.execute(text(f"ALTER TABLE llm_settings ADD COLUMN {col} {typ}"))
                    conn.commit()
                    logger.info("Added column llm_settings.%s", col)
                except Exception as e:
                    logger.debug("Migration add %s: %s", col, e)


def init_db() -> None:
    """Create tables if they do not exist. For SQLite, ensure data dir exists."""
    if DATABASE_URL.startswith("sqlite"):
        path = DATABASE_URL.replace("sqlite:///", "").strip()
        if path.startswith("./"):
            Path(path).parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=_engine)
    _sqlite_migrate_llm_azure_columns()  # Also migrates project_id
    logger.debug("Database tables created or already exist")
