"""Utility to scan and import IGC files from flight_data folder."""

from pathlib import Path
from typing import List, Dict, Tuple

from logbook.db import Database
from logbook.igc_reader import parse_igc_file


def scan_flight_data_folder(flight_data_dir: Path = None) -> List[Path]:
    """Scan flight_data folder for IGC files.
    
    Args:
        flight_data_dir: Path to flight_data directory. Defaults to CWD/flight_data.
    
    Returns:
        List of IGC file paths found.
    """
    if flight_data_dir is None:
        flight_data_dir = Path("flight_data")
    
    if not flight_data_dir.exists():
        return []
    
    return sorted(flight_data_dir.glob("*.igc"))


def import_new_flights(
    db: Database,
    flight_data_dir: Path = None,
    verbose: bool = False,
) -> Tuple[int, List[str]]:
    """Scan and import new flights from flight_data folder.

    Skips files that already exist in database (by filename).

    Args:
        db: Database instance.
        flight_data_dir: Path to flight_data directory. Defaults to CWD/flight_data.
        verbose: Print details about imported files.

    Returns:
        Tuple of (count_imported, list_of_errors).
    """
    persistent_pilot = db.get_default_pilot().strip()
    igc_files = scan_flight_data_folder(flight_data_dir)
    imported_count = 0
    errors = []

    for igc_path in igc_files:
        filename = igc_path.name

        # Skip if already imported
        if db.flight_exists(filename):
            if verbose:
                print(f"Skipping {filename} (already imported)")
            continue

        try:
            # Parse IGC file
            flight_data = parse_igc_file(igc_path)
            flight_pilot = (flight_data.get("pilot") or "").strip()

            if not flight_pilot:
                raise ValueError("Pilot not set in IGC file (HFPLTPILOTINCHARGE missing)")

            if not persistent_pilot:
                persistent_pilot = flight_pilot
                db.set_default_pilot(persistent_pilot)
                if verbose:
                    print(f"Persistent pilot set to '{persistent_pilot}'")

            if flight_pilot != persistent_pilot:
                error_msg = (
                    f"Skipping {filename}: pilot '{flight_pilot}' does not match "
                    f"persistent pilot '{persistent_pilot}'"
                )
                errors.append(error_msg)
                if verbose:
                    print(f"✗ {error_msg}")
                continue

            # Apply persistent pilot to record
            flight_data["pilot"] = persistent_pilot

            # Add to database
            db.add_flight(flight_data)
            imported_count += 1

            if verbose:
                print(f"✓ Imported {filename}")

        except Exception as e:
            error_msg = f"Error importing {filename}: {str(e)}"
            errors.append(error_msg)
            if verbose:
                print(f"✗ {error_msg}")

    return imported_count, errors
