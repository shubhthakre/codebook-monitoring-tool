from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import SettingsResponse, SettingsUpdate, TestEmailResponse
from ..services.alerts import send_test_email
from ..services.app_settings import (
    get_effective_settings,
    save_settings,
    settings_source,
    to_response,
)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsResponse)
def get_app_settings(db: Session = Depends(get_db)):
    settings = get_effective_settings(db)
    return to_response(settings, settings_source(db))


@router.put("", response_model=SettingsResponse)
def update_app_settings(payload: SettingsUpdate, db: Session = Depends(get_db)):
    previous = get_effective_settings(db)
    settings = save_settings(db, payload)
    oracle_restart = (
        previous.oracle_client_lib_dir.strip() != settings.oracle_client_lib_dir.strip()
        and bool(settings.oracle_client_lib_dir.strip())
    )
    return to_response(settings, "ui", oracle_restart_required=oracle_restart)


@router.post("/test-email", response_model=TestEmailResponse)
async def test_alert_email(db: Session = Depends(get_db)):
    settings = get_effective_settings(db)
    try:
        await send_test_email(settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to send test email: {exc}",
        ) from exc
    return TestEmailResponse(ok=True, message="Test email sent")
