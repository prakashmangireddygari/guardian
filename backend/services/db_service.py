from datetime import datetime
from sqlalchemy.orm import Session
from models.db_models import Vehicle, Violation, Alert, HeatmapZone

DANGER_POINTS = {
    'sudden_braking': 15,
    'weaving': 20,
    'tailgating': 25,
    'amber_running': 10,
    'school_zone_speed': 30,
}

HEATMAP_GRID = 50  # pixels — group incidents into grid cells


def save_violation(db: Session, plate: str, track_id: int, vtype: str,
                   location_x: float = None, location_y: float = None,
                   camera_id: str = 'CAM-01'):
    pts = DANGER_POINTS.get(vtype, 0)

    vehicle = db.query(Vehicle).filter(Vehicle.plate == plate).first()
    if vehicle:
        vehicle.total_danger_score += pts
        vehicle.last_seen = datetime.utcnow()
    else:
        vehicle = Vehicle(plate=plate, total_danger_score=pts)
        db.add(vehicle)

    violation = Violation(
        plate=plate, track_id=track_id, violation_type=vtype,
        danger_points=pts, location_x=location_x, location_y=location_y,
        camera_id=camera_id,
    )
    db.add(violation)

    if location_x is not None and location_y is not None:
        _update_heatmap(db, location_x, location_y, pts)

    db.commit()


def save_alert(db: Session, alert_type: str, level: str,
               vehicle_ids: list, details: dict):
    db.add(Alert(alert_type=alert_type, level=level,
                 vehicle_ids=vehicle_ids, details=details))
    db.commit()


def _update_heatmap(db: Session, x: float, y: float, risk: float):
    gx = round(x / HEATMAP_GRID) * HEATMAP_GRID
    gy = round(y / HEATMAP_GRID) * HEATMAP_GRID
    zone = db.query(HeatmapZone).filter(
        HeatmapZone.zone_x == gx, HeatmapZone.zone_y == gy
    ).first()
    if zone:
        zone.incident_count += 1
        zone.risk_score += risk
        zone.last_updated = datetime.utcnow()
    else:
        db.add(HeatmapZone(zone_x=gx, zone_y=gy, incident_count=1, risk_score=risk))
