from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ...core.crud_base import make_router, write_audit
from ...core.database import get_db
from ...core.security import get_current_user
from ...models.instrument import CalibrationRecord, Instrument
from ...models.user import User
from ...schemas import (
    CalibrationRecordCreate,
    CalibrationRecordRead,
    InstrumentCreate,
    InstrumentRead,
    InstrumentUpdate,
)
from ...services.notification_service import refresh_calibration_notifications

# 仪器台账 CRUD（通用路由），校准记录在其上扩展
router = make_router(
    Instrument,
    InstrumentRead,
    InstrumentCreate,
    InstrumentUpdate,
    search_fields=["name", "dept_no", "model", "manufacturer", "serial_no", "owner", "location"],
    filter_fields=["status", "category"],
    prefix="/instruments",
)


@router.get("/{instrument_id}/calibrations", response_model=list[CalibrationRecordRead])
def list_calibrations(
    instrument_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return (
        db.query(CalibrationRecord)
        .filter(CalibrationRecord.instrument_id == instrument_id)
        .order_by(CalibrationRecord.id.desc())
        .all()
    )


@router.post("/{instrument_id}/calibrations", response_model=CalibrationRecordRead, status_code=201)
def create_calibration(
    instrument_id: int,
    item: CalibrationRecordCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not db.get(Instrument, instrument_id):
        raise HTTPException(status_code=404, detail="未找到仪器")
    rec = CalibrationRecord(instrument_id=instrument_id, **item.model_dump(exclude={"instrument_id"}))
    db.add(rec)
    db.commit()
    db.refresh(rec)
    refresh_calibration_notifications(db)
    write_audit(db, user, "create", "calibration_records", rec.id, item.model_dump(), request.client.host if request.client else None)
    return rec


@router.delete("/{instrument_id}/calibrations/{rec_id}")
def delete_calibration(
    instrument_id: int,
    rec_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rec = db.get(CalibrationRecord, rec_id)
    if not rec:
        raise HTTPException(status_code=404, detail="未找到校准记录")
    db.delete(rec)
    db.commit()
    refresh_calibration_notifications(db)
    write_audit(db, user, "delete", "calibration_records", rec_id, "", request.client.host if request.client else None)
    return {"ok": True}
