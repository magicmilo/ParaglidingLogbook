# Paragliding Logbook

A lightweight Python app for storing paragliding flights (IGC files) in a local SQLite database and exploring them via GUI.

## Features (starter framework)
- SQLite database for persistent local storage
- `flights` table with flight metadata
- Migration system with `schema_version`
- IGC file parsing via `pyigc` (and fallback guidance)
- GUI table placeholder using `tkinter` / `ttk.Treeview`

## Requirements
- Python 3.10+
- pip

## Setup

```bash
cd c:\Users\bascombe\source\python\logbook
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python -m logbook.main
```

## Development
- Database file: `logbook.db` in current working directory
- Migrations are in `src/logbook/migrations`

## IGC support
- This project uses `pyigc` to parse `.igc` flight files.
- Save `.igc` files in `flight_data/` and use import logic in `src/logbook/igc_reader.py`.
