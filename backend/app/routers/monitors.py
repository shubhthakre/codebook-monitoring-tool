from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..checkers.systemd import fetch_journal_logs
from ..database import get_db
from ..models import CheckResult, Monitor
from ..schemas import (
    CheckResultResponse,
    ManualCheckResponse,
    MonitorCreate,
    MonitorResponse,
    MonitorUpdate,
    SystemdLogsResponse,
)
from ..services.checker import execute_and_store
from ..services.scheduler import schedule_monitor, unschedule_monitor

router = APIRouter(prefix="/monitors", tags=["monitors"])


@router.get("", response_model=list[MonitorResponse])
def list_monitors(db: Session = Depends(get_db)):
    return db.query(Monitor).order_by(Monitor.name).all()


@router.post("", response_model=MonitorResponse, status_code=201)
def create_monitor(payload: MonitorCreate, db: Session = Depends(get_db)):
    monitor = Monitor(
        name=payload.name,
        type=payload.type.value,
        config=payload.config,
        interval_seconds=payload.interval_seconds,
        enabled=payload.enabled,
    )
    db.add(monitor)
    db.commit()
    db.refresh(monitor)

    if monitor.enabled:
        schedule_monitor(monitor)

    return monitor


@router.get("/{monitor_id}", response_model=MonitorResponse)
def get_monitor(monitor_id: int, db: Session = Depends(get_db)):
    monitor = db.query(Monitor).filter(Monitor.id == monitor_id).first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    return monitor


@router.patch("/{monitor_id}", response_model=MonitorResponse)
def update_monitor(
    monitor_id: int, payload: MonitorUpdate, db: Session = Depends(get_db)
):
    monitor = db.query(Monitor).filter(Monitor.id == monitor_id).first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")

    if payload.name is not None:
        monitor.name = payload.name
    if payload.config is not None:
        monitor.config = payload.config
    if payload.interval_seconds is not None:
        monitor.interval_seconds = payload.interval_seconds
    if payload.enabled is not None:
        monitor.enabled = payload.enabled

    db.commit()
    db.refresh(monitor)

    if monitor.enabled:
        schedule_monitor(monitor)
    else:
        unschedule_monitor(monitor.id)

    return monitor


@router.delete("/{monitor_id}", status_code=204)
def delete_monitor(monitor_id: int, db: Session = Depends(get_db)):
    monitor = db.query(Monitor).filter(Monitor.id == monitor_id).first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")

    unschedule_monitor(monitor_id)
    db.delete(monitor)
    db.commit()


@router.post("/{monitor_id}/check", response_model=ManualCheckResponse)
async def check_now(monitor_id: int, db: Session = Depends(get_db)):
    monitor = db.query(Monitor).filter(Monitor.id == monitor_id).first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")

    outcome = await execute_and_store(db, monitor)
    return ManualCheckResponse(
        monitor_id=monitor.id,
        status=outcome.status,
        message=outcome.message,
        response_ms=outcome.response_ms,
        details=outcome.details,
    )


@router.get("/{monitor_id}/history", response_model=list[CheckResultResponse])
def get_history(monitor_id: int, limit: int = 50, db: Session = Depends(get_db)):
    monitor = db.query(Monitor).filter(Monitor.id == monitor_id).first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")

    return (
        db.query(CheckResult)
        .filter(CheckResult.monitor_id == monitor_id)
        .order_by(CheckResult.checked_at.desc())
        .limit(min(limit, 200))
        .all()
    )


@router.get("/{monitor_id}/logs", response_model=SystemdLogsResponse)
async def get_systemd_logs(
    monitor_id: int,
    since: str | None = Query(
        None,
        description='journalctl --since value, e.g. "2 minutes ago" or "2026-08-06 13:00:00"',
    ),
    until: str | None = Query(
        None,
        description='journalctl --until value, e.g. "2026-08-06 13:05:00"',
    ),
    lines: int = Query(200, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    monitor = db.query(Monitor).filter(Monitor.id == monitor_id).first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    if monitor.type != "systemd":
        raise HTTPException(
            status_code=400, detail="Logs endpoint is only available for systemd monitors"
        )

    unit = (monitor.config or {}).get("unit", "")
    try:
        result = await fetch_journal_logs(
            unit, lines=lines, since=since or None, until=until or None
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return SystemdLogsResponse(
        monitor_id=monitor.id,
        unit=result["unit"],
        active=result["active"],
        since=result.get("since"),
        until=result.get("until"),
        count=result["count"],
        lines=result["lines"],
    )
