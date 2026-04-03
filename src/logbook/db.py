import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

from logbook.migrations import MIGRATIONS


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.conn: Optional[sqlite3.Connection] = None

    def _connect(self):
        if self.conn is None:
            self.conn = sqlite3.connect(self.path)
            self.conn.row_factory = sqlite3.Row
        return self.conn

    def initialize(self):
        conn = self._connect()
        conn.execute("PRAGMA foreign_keys = ON")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER NOT NULL
            )
            """
        )

        cur = conn.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
        row = cur.fetchone()
        current = row["version"] if row else 0

        for version, migration in MIGRATIONS:
            if version > current:
                migration(conn)
                conn.execute("DELETE FROM schema_version")
                conn.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))
                conn.commit()

    def add_flight(self, flight_data: Dict):
        conn = self._connect()
        conn.execute(
            """
            INSERT INTO flights (date, pilot, glider, igc_file, duration_minutes, distance_km, launch_site, landing_site, notes)
            VALUES (:date, :pilot, :glider, :igc_file, :duration_minutes, :distance_km, :launch_site, :landing_site, :notes)
            """,
            flight_data,
        )
        conn.commit()

    def get_flights(self) -> List[sqlite3.Row]:
        conn = self._connect()
        cur = conn.execute("SELECT * FROM flights ORDER BY date DESC")
        return cur.fetchall()

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
