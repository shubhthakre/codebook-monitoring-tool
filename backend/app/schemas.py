from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .models import MonitorStatus, MonitorType


class MonitorCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: MonitorType
    config: dict[str, Any] = Field(default_factory=dict)
    interval_seconds: int = Field(default=60, ge=10, le=86400)
    enabled: bool = True


class MonitorUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    config: dict[str, Any] | None = None
    interval_seconds: int | None = Field(None, ge=10, le=86400)
    enabled: bool | None = None


class MonitorResponse(BaseModel):
    id: int
    name: str
    type: str
    config: dict[str, Any]
    interval_seconds: int
    enabled: bool
    last_status: str
    last_message: str | None
    last_checked_at: datetime | None
    last_response_ms: float | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CheckResultResponse(BaseModel):
    id: int
    monitor_id: int
    status: str
    message: str | None
    response_ms: float | None
    details: dict[str, Any] | None
    checked_at: datetime

    model_config = {"from_attributes": True}


class HealthSummary(BaseModel):
    total: int
    up: int
    down: int
    unknown: int


class ManualCheckResponse(BaseModel):
    monitor_id: int
    status: str
    message: str | None
    response_ms: float | None
    details: dict[str, Any] | None = None


class SystemdLogsResponse(BaseModel):
    monitor_id: int
    unit: str
    active: bool
    since: str | None = None
    until: str | None = None
    grep: str | None = None
    count: int
    lines: list[str]


class SettingsResponse(BaseModel):
    alert_enabled: bool
    alert_to: str
    alert_from: str
    alert_on_recovery: bool
    alert_cooldown_seconds: int
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password_set: bool
    smtp_use_tls: bool
    smtp_use_ssl: bool
    oracle_client_lib_dir: str
    configured: bool
    source: str
    oracle_restart_required: bool = False


class SettingsUpdate(BaseModel):
    alert_enabled: bool
    alert_to: str = ""
    alert_from: str = "monitoring@localhost"
    alert_on_recovery: bool = True
    alert_cooldown_seconds: int = Field(default=300, ge=0)
    smtp_host: str = ""
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_user: str = ""
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    oracle_client_lib_dir: str = ""


class TestEmailResponse(BaseModel):
    ok: bool
    message: str
