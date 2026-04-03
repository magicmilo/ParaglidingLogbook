from pathlib import Path
from typing import Dict

try:
    import pyigc
except ImportError:
    pyigc = None


def parse_igc_file(file_path: Path) -> Dict:
    """Parse IGC file and extract basic flight metadata."""
    if not file_path.exists():
        raise FileNotFoundError(file_path)

    if pyigc is None:
        raise ImportError("pyigc not installed; install via `pip install pyigc`")

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        raw = f.read()

    igc = pyigc.loads(raw)

    return {
        "date": igc.date.isoformat() if hasattr(igc, "date") else None,
        "pilot": igc.pilot if hasattr(igc, "pilot") else "",
        "glider": igc.glider_id if hasattr(igc, "glider_id") else "",
        "igc_file": str(file_path),
        "duration_minutes": float(igc.duration.seconds / 60) if getattr(igc, "duration", None) else None,
        "distance_km": float(getattr(igc, "distance", 0.0) / 1000.0) if getattr(igc, "distance", None) is not None else 0.0,
        "launch_site": igc.launch_location if hasattr(igc, "launch_location") else "",
        "landing_site": igc.landing_location if hasattr(igc, "landing_location") else "",
        "notes": "",
    }
