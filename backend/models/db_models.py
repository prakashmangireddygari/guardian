from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class Vehicle(Base):
    __tablename__ = 'vehicles'
    id = Column(Integer, primary_key=True)
    plate = Column(String(20), unique=True, index=True, nullable=False)
    total_danger_score = Column(Integer, default=0, nullable=False)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)


class Violation(Base):
    __tablename__ = 'violations'
    id = Column(Integer, primary_key=True)
    plate = Column(String(20), index=True)
    track_id = Column(Integer)
    violation_type = Column(String(50), nullable=False)
    danger_points = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    location_x = Column(Float)
    location_y = Column(Float)
    camera_id = Column(String(50), default='CAM-01')


class Alert(Base):
    __tablename__ = 'alerts'
    id = Column(Integer, primary_key=True)
    alert_type = Column(String(50))
    level = Column(String(20))
    vehicle_ids = Column(JSON)
    details = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)


class HeatmapZone(Base):
    __tablename__ = 'heatmap_zones'
    id = Column(Integer, primary_key=True)
    zone_x = Column(Float, nullable=False)
    zone_y = Column(Float, nullable=False)
    incident_count = Column(Integer, default=0)
    risk_score = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow)
