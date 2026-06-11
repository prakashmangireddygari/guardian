from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models.db_models import HeatmapZone, Violation
from models.schemas import HeatmapZoneOut

router = APIRouter(prefix='/public', tags=['public'])


@router.get('/heatmap')
def heatmap(db: Session = Depends(get_db)):
    """Anonymised risk zones — no plates, no faces, no vehicle IDs."""
    zones = db.query(HeatmapZone).filter(HeatmapZone.incident_count > 0).all()
    return {
        'zones': [
            HeatmapZoneOut(
                x=z.zone_x, y=z.zone_y,
                risk_score=round(z.risk_score, 1),
                incident_count=z.incident_count,
            )
            for z in zones
        ]
    }


@router.get('/stats')
def public_stats(db: Session = Depends(get_db)):
    """Aggregate city-level stats — no identifying information."""
    total = db.query(func.count(Violation.id)).scalar()
    by_type = (
        db.query(Violation.violation_type, func.count(Violation.id).label('count'))
        .group_by(Violation.violation_type)
        .all()
    )
    zone_count = db.query(func.count(HeatmapZone.id)).filter(HeatmapZone.risk_score > 50).scalar()
    return {
        'total_incidents_recorded': total,
        'high_risk_zones': zone_count,
        'by_violation_type': [{'type': t, 'count': c} for t, c in by_type],
    }
