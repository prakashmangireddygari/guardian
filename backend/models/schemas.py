from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any


class ViolationOut(BaseModel):
    id: int
    plate: Optional[str]
    violation_type: str
    danger_points: int
    timestamp: datetime
    camera_id: str
    location_x: Optional[float]
    location_y: Optional[float]

    class Config:
        from_attributes = True


class VehicleOut(BaseModel):
    id: int
    plate: str
    total_danger_score: int
    first_seen: datetime
    last_seen: datetime

    class Config:
        from_attributes = True


class VehicleDetail(VehicleOut):
    violations: List[ViolationOut] = []


class AlertOut(BaseModel):
    id: int
    alert_type: str
    level: str
    vehicle_ids: List[int]
    details: Dict[str, Any]
    timestamp: datetime

    class Config:
        from_attributes = True


class HeatmapZoneOut(BaseModel):
    x: float
    y: float
    risk_score: float
    incident_count: int


class WeatherStatus(BaseModel):
    condition: str
    visibility_km: float
    is_night: bool
    temperature_c: float
    threshold_multiplier: float
    alert_message: str
