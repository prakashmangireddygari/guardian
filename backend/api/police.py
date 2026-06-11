from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime

from database import get_db
from models.db_models import Vehicle, Violation, Alert
from models.schemas import VehicleOut, VehicleDetail, ViolationOut, AlertOut

router = APIRouter(prefix='/police', tags=['police'])


@router.get('/search/plates', response_model=list[VehicleOut])
def search_plates(q: str = Query(..., min_length=2), db: Session = Depends(get_db)):
    return db.query(Vehicle).filter(Vehicle.plate.ilike(f'%{q}%')).limit(50).all()


@router.get('/search/violations')
def search_violations(
    plate: Optional[str] = None,
    violation_type: Optional[str] = None,
    min_score: Optional[int] = None,
    max_score: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(Violation)
    if plate:
        q = q.filter(Violation.plate.ilike(f'%{plate}%'))
    if violation_type:
        q = q.filter(Violation.violation_type == violation_type)
    if min_score is not None:
        q = q.filter(Violation.danger_points >= min_score)
    if max_score is not None:
        q = q.filter(Violation.danger_points <= max_score)
    if start_date:
        q = q.filter(Violation.timestamp >= start_date)
    if end_date:
        q = q.filter(Violation.timestamp <= end_date)

    total = q.count()
    rows = q.order_by(Violation.timestamp.desc()).offset(offset).limit(limit).all()
    return {'total': total, 'violations': [ViolationOut.model_validate(r) for r in rows]}


@router.get('/vehicle/{plate}', response_model=VehicleDetail)
def vehicle_detail(plate: str, db: Session = Depends(get_db)):
    vehicle = db.query(Vehicle).filter(Vehicle.plate == plate.upper()).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail='Vehicle not found')
    violations = (
        db.query(Violation)
        .filter(Violation.plate == plate.upper())
        .order_by(Violation.timestamp.desc())
        .all()
    )
    data = VehicleDetail.model_validate(vehicle)
    data.violations = [ViolationOut.model_validate(v) for v in violations]
    return data


@router.get('/top-offenders', response_model=list[VehicleOut])
def top_offenders(limit: int = Query(10, le=50), db: Session = Depends(get_db)):
    return (
        db.query(Vehicle)
        .order_by(Vehicle.total_danger_score.desc())
        .limit(limit)
        .all()
    )


@router.get('/alerts/recent', response_model=list[AlertOut])
def recent_alerts(limit: int = Query(20, le=100), db: Session = Depends(get_db)):
    return db.query(Alert).order_by(Alert.timestamp.desc()).limit(limit).all()


@router.get('/stats/summary')
def stats_summary(db: Session = Depends(get_db)):
    total_vehicles = db.query(func.count(Vehicle.id)).scalar()
    total_violations = db.query(func.count(Violation.id)).scalar()
    by_type = (
        db.query(Violation.violation_type, func.count(Violation.id).label('count'))
        .group_by(Violation.violation_type)
        .all()
    )
    high_risk = db.query(func.count(Vehicle.id)).filter(Vehicle.total_danger_score >= 50).scalar()
    return {
        'total_vehicles': total_vehicles,
        'total_violations': total_violations,
        'high_risk_vehicles': high_risk,
        'by_type': [{'type': t, 'count': c} for t, c in by_type],
    }
