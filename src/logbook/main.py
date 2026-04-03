import argparse
from pathlib import Path

from logbook.db import Database
from logbook.gui import run_gui


def parse_args():
    parser = argparse.ArgumentParser(description="Paragliding logbook app")
    parser.add_argument("--db", default="logbook.db", help="SQLite database file")
    parser.add_argument("--no-gui", action="store_true", help="Run without GUI (CLI only)")
    parser.add_argument("--import-only", action="store_true", help="Import new flights and exit")
    return parser.parse_args()


def main():
    args = parse_args()
    db = Database(Path(args.db))
    db.initialize()

    if args.import_only:
        from logbook.file_scanner import import_new_flights
        count, errors = import_new_flights(db, verbose=True)
        print(f"\nImported {count} flight(s)")
        if errors:
            print(f"{len(errors)} error(s) occurred:")
            for error in errors:
                print(f"  - {error}")
        return

    if args.no_gui:
        print("Database initialized:", args.db)
        flights = db.get_flights()
        print(f"Total flights in database: {len(flights)}")
        return

    run_gui(db)


if __name__ == "__main__":
    main()
