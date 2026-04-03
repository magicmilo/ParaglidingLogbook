def upgrade(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS flights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            pilot TEXT,
            glider TEXT,
            igc_file TEXT UNIQUE,
            duration_minutes REAL,
            distance_km REAL,
            launch_site TEXT,
            landing_site TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
