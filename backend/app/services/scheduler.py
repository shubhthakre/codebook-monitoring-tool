import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Monitor
from .checker import execute_and_store

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def scheduled_check(monitor_id: int):
    db: Session = SessionLocal()
    try:
        monitor = db.query(Monitor).filter(Monitor.id == monitor_id).first()
        if monitor and monitor.enabled:
            await execute_and_store(db, monitor)
    except Exception as exc:
        logger.error("Scheduled check failed for monitor %s: %s", monitor_id, exc)
    finally:
        db.close()


def schedule_monitor(monitor: Monitor):
    job_id = f"monitor_{monitor.id}"
    existing = scheduler.get_job(job_id)
    if existing:
        scheduler.remove_job(job_id)

    if monitor.enabled:
        scheduler.add_job(
            scheduled_check,
            "interval",
            seconds=monitor.interval_seconds,
            id=job_id,
            args=[monitor.id],
            replace_existing=True,
        )


def unschedule_monitor(monitor_id: int):
    job_id = f"monitor_{monitor_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)


def load_all_monitors():
    db: Session = SessionLocal()
    try:
        monitors = db.query(Monitor).filter(Monitor.enabled.is_(True)).all()
        for monitor in monitors:
            schedule_monitor(monitor)
        logger.info("Scheduled %d monitors", len(monitors))
    finally:
        db.close()


def start_scheduler():
    if not scheduler.running:
        scheduler.start()
        load_all_monitors()


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
