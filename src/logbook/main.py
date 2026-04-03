import argparse
from pathlib import Path

from logbook.db import Database
from logbook.gui import run_gui


def parse_args():
    parser = argparse.ArgumentParser(description="Paragliding logbook app")
    parser.add_argument("--db", default="logbook.db", help="SQLite database file")
    parser.add_argument("--no-gui", action="store_true", help="Run without GUI (CLI only)")
    return parser.parse_args()


def main():
    args = parse_args()
    db = Database(Path(args.db))
    db.initialize()

    if args.no_gui:
        print("Database initialized:", args.db)
        print("Use `python -m logbook.main --no-gui` to keep running CLI; GUI not implemented")
        return

    run_gui(db)


if __name__ == "__main__":
    main()
