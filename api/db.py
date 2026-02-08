"""Database models and session for settings storage."""
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _utc_now() -> datetime:
    """Current UTC time (prefer over deprecated datetime.utcnow())."""
    return datetime.now(timezone.utc)

from dotenv import load_dotenv
from sqlalchemy import BigInteger, Boolean, Date, DateTime, Index, Numeric, String, Text, create_engine, text
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, onupdate=_utc_now)


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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, onupdate=_utc_now)
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, onupdate=_utc_now)


class ToolSettingsModel(Base):
    """Tool/plugin settings: enabled status and encrypted settings_json."""
    __tablename__ = "tool_settings"

    tool_name: Mapped[str] = mapped_column(String(128), primary_key=True)
    plugin_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    settings_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, onupdate=_utc_now)


class EmployeeModel(Base):
    """HR employees table: single source of truth for staff data (SPEC_HR_SERVICE)."""
    __tablename__ = "hr_employees"
    __table_args__ = (
        Index("ix_hr_employees_personal_number", "personal_number", unique=True),
        Index("ix_hr_employees_email", "email"),
        Index("ix_hr_employees_jira_worker_id", "jira_worker_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    personal_number: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(String(512), nullable=False)
    email: Mapped[str] = mapped_column(String(512), nullable=False)
    jira_worker_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    position: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    mvz: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    supervisor: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    hire_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    fte: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False, default=1)
    dismissal_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    birth_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    mattermost_username: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    is_supervisor: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_delivery_manager: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    team: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, onupdate=_utc_now)


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
