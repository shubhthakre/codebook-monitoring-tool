from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..models import AppSettings
from ..oracle_paths import current_oracle_platform, resolve_oracle_client_lib_dir
from ..schemas import SettingsResponse, SettingsUpdate

SINGLETON_ID = 1

_OVERLAY_FIELDS = (
    "alert_enabled",
    "alert_to",
    "alert_from",
    "alert_on_recovery",
    "alert_cooldown_seconds",
    "smtp_host",
    "smtp_port",
    "smtp_user",
    "smtp_password",
    "smtp_use_tls",
    "smtp_use_ssl",
    "oracle_client_lib_dir",
)


def _row_to_overlay(row: AppSettings) -> dict:
    return {name: getattr(row, name) for name in _OVERLAY_FIELDS}


def get_effective_settings(db: Session | None = None) -> Settings:
    """UI-saved values override backend/.env defaults."""
    base = get_settings()
    owns_session = db is None
    if owns_session:
        from ..database import SessionLocal

        db = SessionLocal()
    try:
        row = db.get(AppSettings, SINGLETON_ID)
        if row is None:
            return base
        return base.model_copy(update=_row_to_overlay(row))
    finally:
        if owns_session:
            db.close()


def settings_source(db: Session) -> str:
    return "ui" if db.get(AppSettings, SINGLETON_ID) is not None else "env"


def to_response(
    settings: Settings,
    source: str,
    oracle_restart_required: bool = False,
) -> SettingsResponse:
    from .alerts import alerts_configured

    return SettingsResponse(
        alert_enabled=settings.alert_enabled,
        alert_to=settings.alert_to,
        alert_from=settings.alert_from,
        alert_on_recovery=settings.alert_on_recovery,
        alert_cooldown_seconds=settings.alert_cooldown_seconds,
        smtp_host=settings.smtp_host,
        smtp_port=settings.smtp_port,
        smtp_user=settings.smtp_user,
        smtp_password_set=bool(settings.smtp_password),
        smtp_use_tls=settings.smtp_use_tls,
        smtp_use_ssl=settings.smtp_use_ssl,
        oracle_client_lib_dir=settings.oracle_client_lib_dir,
        oracle_client_resolved=resolve_oracle_client_lib_dir(
            settings.oracle_client_lib_dir
        ),
        oracle_client_platform=current_oracle_platform(),
        configured=alerts_configured(settings),
        source=source,
        oracle_restart_required=oracle_restart_required,
    )


def save_settings(db: Session, payload: SettingsUpdate) -> Settings:
    row = db.get(AppSettings, SINGLETON_ID)
    if row is None:
        env = get_settings()
        row = AppSettings(
            id=SINGLETON_ID,
            smtp_password=env.smtp_password,
        )
        db.add(row)

    row.alert_enabled = payload.alert_enabled
    row.alert_to = payload.alert_to.strip()
    row.alert_from = payload.alert_from.strip() or "monitoring@localhost"
    row.alert_on_recovery = payload.alert_on_recovery
    row.alert_cooldown_seconds = payload.alert_cooldown_seconds
    row.smtp_host = payload.smtp_host.strip()
    row.smtp_port = payload.smtp_port
    row.smtp_user = payload.smtp_user.strip()
    row.smtp_use_tls = payload.smtp_use_tls
    row.smtp_use_ssl = payload.smtp_use_ssl
    row.oracle_client_lib_dir = payload.oracle_client_lib_dir.strip()
    if payload.smtp_password:
        row.smtp_password = payload.smtp_password
    row.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(row)
    return get_effective_settings(db)
