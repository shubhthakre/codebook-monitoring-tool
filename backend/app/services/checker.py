from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..models import CheckResult, Monitor
from ..checkers import (
    check_http,
    check_tcp,
    check_sqlite,
    check_postgres,
    check_mysql,
    check_oracle,
    check_systemd,
)
from ..checkers.base import CheckOutcome
from .alerts import maybe_alert_on_transition

CHECKERS = {
    "http": check_http,
    "tcp": check_tcp,
    "sqlite": check_sqlite,
    "postgres": check_postgres,
    "mysql": check_mysql,
    "oracle": check_oracle,
    "systemd": check_systemd,
}


async def run_check(monitor: Monitor) -> CheckOutcome:
    checker = CHECKERS.get(monitor.type)
    if not checker:
        return CheckOutcome("down", f"Unknown monitor type: {monitor.type}")

    return await checker(monitor.config or {})


async def execute_and_store(db: Session, monitor: Monitor) -> CheckOutcome:
    previous_status = monitor.last_status
    outcome = await run_check(monitor)

    now = datetime.now(timezone.utc)
    monitor.last_status = outcome.status
    monitor.last_message = outcome.message
    monitor.last_checked_at = now
    monitor.last_response_ms = outcome.response_ms

    result = CheckResult(
        monitor_id=monitor.id,
        status=outcome.status,
        message=outcome.message,
        response_ms=outcome.response_ms,
        details=outcome.details,
        checked_at=now,
    )
    db.add(result)
    db.commit()
    db.refresh(monitor)

    await maybe_alert_on_transition(monitor, previous_status, outcome)

    return outcome
