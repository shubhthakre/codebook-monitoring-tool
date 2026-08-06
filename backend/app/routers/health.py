from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Monitor, MonitorStatus
from ..schemas import HealthSummary

router = APIRouter(tags=["health"])


@router.get("/health")
def api_health():
    return {"status": "ok"}


@router.get("/summary", response_model=HealthSummary)
def get_summary(db: Session = Depends(get_db)):
    monitors = db.query(Monitor).all()
    up = sum(1 for m in monitors if m.last_status == MonitorStatus.UP)
    down = sum(1 for m in monitors if m.last_status == MonitorStatus.DOWN)
    unknown = sum(1 for m in monitors if m.last_status == MonitorStatus.UNKNOWN)

    return HealthSummary(
        total=len(monitors),
        up=up,
        down=down,
        unknown=unknown,
    )
