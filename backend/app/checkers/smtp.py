import asyncio
import smtplib
import ssl
import time
from typing import Any

from .base import CheckOutcome


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _check_smtp_sync(config: dict[str, Any]) -> CheckOutcome:
    host = str(config.get("host", "")).strip()
    port = int(config.get("port", 587) or 587)
    timeout = float(config.get("timeout", 10) or 10)
    user = str(config.get("user", "") or "").strip()
    password = str(config.get("password", "") or "")
    use_ssl = _as_bool(config.get("use_ssl"), default=False)
    # Default STARTTLS on for non-SSL ports (587), off when SSL is used (465)
    use_tls = _as_bool(config.get("use_tls"), default=not use_ssl)

    if not host:
        return CheckOutcome("down", "Host is required")
    if use_ssl and use_tls:
        return CheckOutcome(
            "down",
            "Use either SSL (port 465) or STARTTLS (port 587), not both",
        )

    start = time.perf_counter()
    try:
        if use_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, timeout=timeout, context=context) as smtp:
                smtp.ehlo()
                if user:
                    smtp.login(user, password)
                # NOOP proves the session is usable without sending mail
                code, resp = smtp.noop()
        else:
            with smtplib.SMTP(host, port, timeout=timeout) as smtp:
                smtp.ehlo()
                if use_tls:
                    context = ssl.create_default_context()
                    smtp.starttls(context=context)
                    smtp.ehlo()
                if user:
                    smtp.login(user, password)
                code, resp = smtp.noop()

        elapsed = (time.perf_counter() - start) * 1000
        if code != 250:
            return CheckOutcome(
                "down",
                f"SMTP NOOP failed: {code} {resp!r}",
                elapsed,
                {"smtp_code": code},
            )

        auth_note = "authenticated" if user else "connected (no auth)"
        tls_note = "SSL" if use_ssl else ("STARTTLS" if use_tls else "plain")
        return CheckOutcome(
            "up",
            f"SMTP {auth_note} via {tls_note} on {host}:{port}",
            elapsed,
            {
                "host": host,
                "port": port,
                "use_ssl": use_ssl,
                "use_tls": use_tls,
                "authenticated": bool(user),
            },
        )
    except smtplib.SMTPAuthenticationError as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return CheckOutcome("down", f"SMTP auth failed: {exc}", elapsed)
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return CheckOutcome("down", str(exc), elapsed)


async def check_smtp(config: dict[str, Any]) -> CheckOutcome:
    return await asyncio.to_thread(_check_smtp_sync, config)
