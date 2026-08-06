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
    count: int
    lines: list[str]
