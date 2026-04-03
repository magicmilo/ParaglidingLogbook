"""Database layer using SQLAlchemy ORM."""

from pathlib import Path
from typing import List, Optional

from sqlalchemy import create_engine, select, update, text
from sqlalchemy.orm import sessionmaker, Session

from logbook.models import Base, Flight, Setting


class Database:
    """SQLAlchemy-based database handler."""

    def __init__(self, path: Path):
        self.path = path
        self.engine = create_engine(f"sqlite:///{self.path}")
        self.SessionLocal = sessionmaker(bind=self.engine)
        # ensure tables exist immediately for settings lookups and updates
        Base.metadata.create_all(self.engine)

    def initialize(self):
        """Create all tables and alter existing schema if needed."""
        Base.metadata.create_all(self.engine)

        # Ensure new fields are added to existing flights table if migration required
        with self.engine.connect() as conn:
            existing_cols = set()
            has_table = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='flights'")) .fetchone()
            if has_table:
                existing_cols = {r[1] for r in conn.execute(text("PRAGMA table_info(flights)")).fetchall()}

            required = {"takeoff_site", "takeoff_time", "takeoff_altitude", "takeoff_latitude", "takeoff_longitude", "landing_time", "landing_altitude", "max_altitude_gain", "thermalling_height_gain", "duration"}
            for col in required - existing_cols:
                if col == "takeoff_site":
                    conn.execute(text("ALTER TABLE flights ADD COLUMN takeoff_site VARCHAR(255)"))
                elif col == "takeoff_time":
                    conn.execute(text("ALTER TABLE flights ADD COLUMN takeoff_time VARCHAR(16)"))
                elif col == "takeoff_altitude":
                    conn.execute(text("ALTER TABLE flights ADD COLUMN takeoff_altitude FLOAT"))
                elif col == "takeoff_latitude":
                    conn.execute(text("ALTER TABLE flights ADD COLUMN takeoff_latitude FLOAT"))
                elif col == "takeoff_longitude":
                    conn.execute(text("ALTER TABLE flights ADD COLUMN takeoff_longitude FLOAT"))
                elif col == "landing_time":
                    conn.execute(text("ALTER TABLE flights ADD COLUMN landing_time VARCHAR(16)"))
                elif col == "landing_altitude":
                    conn.execute(text("ALTER TABLE flights ADD COLUMN landing_altitude FLOAT"))
                elif col == "max_altitude_gain":
                    conn.execute(text("ALTER TABLE flights ADD COLUMN max_altitude_gain FLOAT"))
                elif col == "thermalling_height_gain":
                    conn.execute(text("ALTER TABLE flights ADD COLUMN thermalling_height_gain FLOAT"))
                elif col == "duration":
                    conn.execute(text("ALTER TABLE flights ADD COLUMN duration VARCHAR(16)"))

    def _get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()

    def add_flight(self, flight_data: dict) -> Flight:
        """Add a new flight record to the database."""
        session = self._get_session()
        try:
            flight = Flight(**flight_data)
            session.add(flight)
            session.commit()
            session.refresh(flight)
            return flight
        finally:
            session.close()

    def get_flights(self, order_by_date_desc: bool = True) -> List[Flight]:
        """Get all flights from the database."""
        session = self._get_session()
        try:
            query = select(Flight)
            if order_by_date_desc:
                query = query.order_by(Flight.date.desc())
            result = session.execute(query)
            return result.scalars().all()
        finally:
            session.close()

    def get_flight_by_filename(self, filename: str) -> Optional[Flight]:
        """Get a flight by its filename."""
        session = self._get_session()
        try:
            query = select(Flight).where(Flight.filename == filename)
            result = session.execute(query)
            return result.scalars().first()
        finally:
            session.close()

    def flight_exists(self, filename: str) -> bool:
        """Check if a flight already exists by filename."""
        return self.get_flight_by_filename(filename) is not None

    def update_flight(self, flight_id: int, flight_data: dict) -> Optional[Flight]:
        """Update an existing flight record."""
        session = self._get_session()
        try:
            flight = session.get(Flight, flight_id)
            if flight:
                for key, value in flight_data.items():
                    if hasattr(flight, key):
                        setattr(flight, key, value)
                session.commit()
                session.refresh(flight)
            return flight
        finally:
            session.close()

    def update_all_pilots(self, pilot_name: str) -> int:
        """Update pilot name for all flights."""
        session = self._get_session()
        try:
            result = session.execute(update(Flight).values(pilot=pilot_name))
            session.commit()
            return result.rowcount
        finally:
            session.close()

    def delete_flight(self, flight_id: int) -> bool:
        """Delete a flight by ID."""
        session = self._get_session()
        try:
            flight = session.get(Flight, flight_id)
            if flight:
                session.delete(flight)
                session.commit()
                return True
            return False
        finally:
            session.close()

    def delete_all_flights(self) -> int:
        """Delete all flights from the database."""
        session = self._get_session()
        try:
            deleted = session.query(Flight).delete()
            session.commit()
            return deleted
        finally:
            session.close()

    def get_default_pilot(self) -> str:
        """Return default pilot name, empty string if none."""
        session = self._get_session()
        try:
            setting = session.query(Setting).filter_by(key="default_pilot").first()
            return setting.value if setting and setting.value is not None else ""
        finally:
            session.close()

    def set_default_pilot(self, pilot_name: str):
        """Set default pilot name in settings."""
        session = self._get_session()
        try:
            setting = session.query(Setting).filter_by(key="default_pilot").first()
            if setting is None:
                setting = Setting(key="default_pilot", value=pilot_name)
                session.add(setting)
            else:
                setting.value = pilot_name
            session.commit()
            return pilot_name
        finally:
            session.close()

    def get_setting(self, key: str) -> str:
        """Get a setting by key."""
        session = self._get_session()
        try:
            setting = session.query(Setting).filter_by(key=key).first()
            return setting.value if setting and setting.value is not None else ""
        finally:
            session.close()

    def set_setting(self, key: str, value: str):
        """Set a setting value by key."""
        session = self._get_session()
        try:
            setting = session.query(Setting).filter_by(key=key).first()
            if setting is None:
                setting = Setting(key=key, value=value)
                session.add(setting)
            else:
                setting.value = value
            session.commit()
            return value
        finally:
            session.close()

    def close(self):
        """Close database connection if needed."""
        self.engine.dispose()
