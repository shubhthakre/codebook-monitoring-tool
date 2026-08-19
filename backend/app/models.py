import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class MonitorType(str, enum.Enum):
    HTTP = "http"
    TCP = "tcp"
    POSTGRES = "postgres"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    ORACLE = "oracle"
    SYSTEMD = "systemd"
    SMTP = "smtp"
    GRAPH = "graph"


class MonitorStatus(str, enum.Enum):
    UP = "up"
    DOWN = "down"
    UNKNOWN = "unknown"


class Monitor(Base):
    __tablename__ = "monitors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    interval_seconds: Mapped[int] = mapped_column(Integer, default=60)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_status: Mapped[str] = mapped_column(String(20), default=MonitorStatus.UNKNOWN)
    last_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_response_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class CheckResult(Base):
    __tablename__ = "check_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    monitor_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )


class AppSettings(Base):
    """Singleton row (id=1) for UI-editable alert/SMTP/Oracle settings."""

    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alert_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    alert_to: Mapped[str] = mapped_column(String(1024), default="")
    alert_from: Mapped[str] = mapped_column(String(255), default="monitoring@localhost")
    alert_on_recovery: Mapped[bool] = mapped_column(Boolean, default=True)
    alert_cooldown_seconds: Mapped[int] = mapped_column(Integer, default=300)
    smtp_host: Mapped[str] = mapped_column(String(255), default="")
    smtp_port: Mapped[int] = mapped_column(Integer, default=587)
    smtp_user: Mapped[str] = mapped_column(String(255), default="")
    smtp_password: Mapped[str] = mapped_column(String(512), default="")
    smtp_use_tls: Mapped[bool] = mapped_column(Boolean, default=True)
    smtp_use_ssl: Mapped[bool] = mapped_column(Boolean, default=False)
    oracle_client_lib_dir: Mapped[str] = mapped_column(String(1024), default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
