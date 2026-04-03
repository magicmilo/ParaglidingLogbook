"""SQLAlchemy ORM models for logbook application."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Flight(Base):
    """Paragliding flight record with metadata and track data."""

    __tablename__ = "flights"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Hidden
    filename = Column(String(255), unique=True, nullable=False)

    # Basics
    date = Column(String(10), nullable=True)  # ISO format YYYY-MM-DD
    pilot = Column(String(255), nullable=True)
    glider = Column(String(255), nullable=True)

    # Flight data
    duration = Column(String(16), nullable=True)  # HH:MM:SS format
    distance_km = Column(Float, nullable=True)
    max_altitude = Column(Float, nullable=True)  # in meters

    # Takeoff
    takeoff_site = Column(String(255), nullable=True)
    takeoff_time = Column(String(16), nullable=True)
    takeoff_altitude = Column(Float, nullable=True)
    takeoff_latitude = Column(Float, nullable=True)
    takeoff_longitude = Column(Float, nullable=True)

    # Landing
    landing_time = Column(String(16), nullable=True)
    landing_altitude = Column(Float, nullable=True)

    # Altitude gain
    max_altitude_gain = Column(Float, nullable=True)
    thermalling_height_gain = Column(Float, nullable=True)  # sum of thermal alt_change values in meters

    # Metadata
    igc_file = Column(String(512), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Convert model instance to dictionary."""
        return {
            "id": self.id,
            "filename": self.filename,
            "date": self.date,
            "pilot": self.pilot,
            "glider": self.glider,
            "duration": self.duration,
            "distance_km": self.distance_km,
            "max_altitude": self.max_altitude,
            "takeoff_site": self.takeoff_site,
            "takeoff_time": self.takeoff_time,
            "takeoff_altitude": self.takeoff_altitude,
            "takeoff_latitude": self.takeoff_latitude,
            "takeoff_longitude": self.takeoff_longitude,
            "landing_time": self.landing_time,
            "landing_altitude": self.landing_altitude,
            "max_altitude_gain": self.max_altitude_gain,
            "thermalling_height_gain": self.thermalling_height_gain,
            "igc_file": self.igc_file,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def __repr__(self):
        return (
            f"<Flight(id={self.id}, date={self.date}, pilot={self.pilot}, "
            f"glider={self.glider}, takeoff_site={self.takeoff_site})>"
        )


class Setting(Base):
    """Application settings key/value store."""

    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(String(1024), nullable=True)
