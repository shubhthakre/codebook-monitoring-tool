import asyncio
import logging
import smtplib
import time
from email.message import EmailMessage

from ..checkers.base import CheckOutcome
from ..config import Settings
from ..models import Monitor

logger = logging.getLogger(__name__)

# In-memory cooldown tracking: monitor_id -> last alert unix timestamp
_last_alert_at: dict[int, float] = {}


def _recipients(settings: Settings) -> list[str]:
    return [addr.strip() for addr in settings.alert_to.split(",") if addr.strip()]


def alerts_configured(settings: Settings | None = None) -> bool:
    if settings is None:
        from .app_settings import get_effective_settings

        settings = get_effective_settings()
    return bool(
        settings.alert_enabled
        and settings.smtp_host
        and _recipients(settings)
    )


def _should_send(monitor_id: int, cooldown_seconds: int) -> bool:
    if cooldown_seconds <= 0:
        return True
    last = _last_alert_at.get(monitor_id)
    if last is None:
        return True
    return (time.time() - last) >= cooldown_seconds


def _build_message(
    settings: Settings,
    monitor: Monitor,
    outcome: CheckOutcome,
    kind: str,
) -> EmailMessage:
    status_label = "DOWN" if kind == "down" else "RECOVERED"
    subject = f"[Monitor] {monitor.name} is {status_label}"
    checked = (
        monitor.last_checked_at.isoformat() if monitor.last_checked_at else "n/a"
    )
    response = (
        f"{outcome.response_ms:.1f} ms"
        if outcome.response_ms is not None
        else "n/a"
    )
    body = (
        f"Monitor: {monitor.name}\n"
        f"Type: {monitor.type}\n"
        f"Status: {status_label}\n"
        f"Message: {outcome.message or 'n/a'}\n"
        f"Response time: {response}\n"
        f"Checked at (UTC): {checked}\n"
        f"Monitor ID: {monitor.id}\n"
    )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.alert_from
    msg["To"] = ", ".join(_recipients(settings))
    msg.set_content(body)
    return msg


def _send_smtp(settings: Settings, message: EmailMessage) -> None:
    recipients = _recipients(settings)
    if settings.smtp_use_ssl:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message, to_addrs=recipients)
        return

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        smtp.ehlo()
        if settings.smtp_use_tls:
            smtp.starttls()
            smtp.ehlo()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(message, to_addrs=recipients)


async def send_status_alert(
    monitor: Monitor,
    outcome: CheckOutcome,
    kind: str,
) -> None:
    """Send a down or recovery email. Never raises to the caller."""
    from .app_settings import get_effective_settings

    settings = get_effective_settings()
    if not alerts_configured(settings):
        return

    if kind == "recovery" and not settings.alert_on_recovery:
        return

    # Cooldown applies to down alerts only so recovery can still notify.
    if kind == "down" and not _should_send(monitor.id, settings.alert_cooldown_seconds):
        logger.info(
            "Skipping down alert for monitor %s (cooldown %ss)",
            monitor.id,
            settings.alert_cooldown_seconds,
        )
        return

    message = _build_message(settings, monitor, outcome, kind)
    try:
        await asyncio.to_thread(_send_smtp, settings, message)
        if kind == "down":
            _last_alert_at[monitor.id] = time.time()
        logger.info(
            "Sent %s alert for monitor %s (%s) to %s",
            kind,
            monitor.id,
            monitor.name,
            message["To"],
        )
    except Exception as exc:
        logger.error(
            "Failed to send %s alert for monitor %s: %s",
            kind,
            monitor.id,
            exc,
        )


async def send_test_email(settings: Settings | None = None) -> None:
    """Send a one-off test message. Raises ValueError if not configured."""
    from .app_settings import get_effective_settings

    settings = settings or get_effective_settings()
    if not alerts_configured(settings):
        raise ValueError(
            "Alerts are not fully configured. Enable alerts and set SMTP host plus recipients."
        )

    recipients = _recipients(settings)
    msg = EmailMessage()
    msg["Subject"] = "[Monitor] Test email"
    msg["From"] = settings.alert_from
    msg["To"] = ", ".join(recipients)
    msg.set_content(
        "This is a test email from ST Monitoring.\n\n"
        "If you received this, SMTP settings are working."
    )
    await asyncio.to_thread(_send_smtp, settings, msg)


async def maybe_alert_on_transition(
    monitor: Monitor,
    previous_status: str | None,
    outcome: CheckOutcome,
) -> None:
    previous = (previous_status or "unknown").lower()
    current = (outcome.status or "").lower()

    if previous != "down" and current == "down":
        await send_status_alert(monitor, outcome, "down")
    elif previous == "down" and current == "up":
        await send_status_alert(monitor, outcome, "recovery")
