from datetime import datetime, date
from pathlib import Path
from typing import Dict

# Prefer libigc where available, fallback to igc_parser
try:
    from libigc import Flight as IgcFlight
except ImportError:
    IgcFlight = None

try:
    import igc_parser
except ImportError:
    igc_parser = None


def _extract_header_value(file_path: Path, prefix: str) -> str:
    """Extract value after an IGC header prefix."""
    value = None
    target = prefix.upper() + ":"
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.strip().upper().startswith(target):
                value = line.split(":", 1)[1].strip()
                break
    return value or ""


def _extract_pilot_from_file(file_path: Path) -> str:
    """Extract HFPLTPILOTINCHARGE pilot name from IGC header."""
    return _extract_header_value(file_path, "HFPLTPILOTINCHARGE")


def _format_time_of_day(raw_time):
    """Format a raw IGC time value into HH:MM:SS."""
    if raw_time is None:
        return ""

    if isinstance(raw_time, str):
        raw_time = raw_time.strip()
        if raw_time == "":
            return ""
        # numeric string from libigc (38028.0 etc.)
        try:
            raw_time = float(raw_time)
        except ValueError:
            # HH:MM:SS-like string
            return raw_time

    # libigc may expose a float seconds-of-day;
    # if it's a datetime/time object use strftime
    try:
        if isinstance(raw_time, (int, float)):
            seconds = int(round(raw_time))
            seconds %= 24 * 3600
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    except Exception:
        pass

    # support datetime.time/datetime objects
    try:
        from datetime import time, datetime

        if isinstance(raw_time, time):
            return raw_time.strftime("%H:%M:%S")
        if isinstance(raw_time, datetime):
            return raw_time.strftime("%H:%M:%S")
    except Exception:
        pass

    return str(raw_time)


def _format_duration(duration_seconds):
    """Format duration in seconds to HH:MM:SS string."""
    if duration_seconds is None:
        return ""
    
    duration_seconds = int(round(duration_seconds))
    hours = duration_seconds // 3600
    minutes = (duration_seconds % 3600) // 60
    seconds = duration_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _haversine_dist(lat1, lon1, lat2, lon2):
    import math

    R = 6371.0
    from math import radians, cos, sin, sqrt, atan2

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


def _raw_time_to_seconds(raw_time):
    """Convert raw IGC time to seconds of day."""
    if raw_time is None:
        return None
    
    # If it's already seconds of day as numeric
    if isinstance(raw_time, (int, float)):
        return float(raw_time)
    
    # If it's a string in HH:MM:SS format
    if isinstance(raw_time, str):
        try:
            parts = raw_time.strip().split(":")
            if len(parts) == 3:
                h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
                return h * 3600 + m * 60 + s
        except (ValueError, IndexError):
            pass
    
    return None


def _guess_takeoff_site(lat, lon):
    """Guess takeoff site name from known coordinates (fallback when header is empty)."""
    if lat is None or lon is None:
        return ""

    known_sites = [
        {"name": "Westbury", "lat": 51.264133, "lon": -2.1452},
    ]

    for site in known_sites:
        dist = _haversine_dist(lat, lon, site["lat"], site["lon"])
        if dist <= 2.0:
            return site["name"]
    return ""


def parse_igc_file(file_path: Path) -> Dict:
    """Parse IGC file and extract basic flight metadata."""
    if not file_path.exists():
        raise FileNotFoundError(file_path)

    pilot_name = _extract_pilot_from_file(file_path)

    if IgcFlight is not None:
        flight = IgcFlight.create_from_file(str(file_path))
        if not flight.valid:
            raise ValueError("libigc reported invalid IGC file: %s" % ",".join(flight.notes))

        flight_date = None
        if hasattr(flight, "date_timestamp") and flight.date_timestamp is not None:
            flight_date = date.fromtimestamp(flight.date_timestamp)

        distance_km = None
        try:
            # Sum glides as total distance
            distance_km = sum(g.track_length for g in getattr(flight, "glides", []))
        except Exception:
            distance_km = None

        # Calculate thermalling height gain from thermals
        thermalling_height_gain = None
        try:
            thermals = getattr(flight, "thermals", [])
            if thermals:
                total_thermal_gain = 0
                for t in thermals:
                    if hasattr(t, "alt_change"):
                        # alt_change may be a method or property depending on libigc version
                        alt_change = t.alt_change() if callable(t.alt_change) else t.alt_change
                        if alt_change is not None:
                            total_thermal_gain += alt_change
                if total_thermal_gain:
                    thermalling_height_gain = total_thermal_gain
        except Exception:
            pass

        # Calculate max altitude from fixes
        max_altitude = None
        min_altitude = None
        max_altitude_gain = None
        takeoff_time = ""
        takeoff_altitude = None
        takeoff_latitude = None
        takeoff_longitude = None
        landing_time = ""
        landing_altitude = None
        duration_seconds = None
        try:
            fixes = getattr(flight, "fixes", [])
            if fixes:
                # Use GNSS altitude for max and min altitude (more accurate than pressure)
                altitudes = [f.gnss_alt for f in fixes if f.gnss_alt is not None]
                if altitudes:
                    max_altitude = max(altitudes)
                    min_altitude = min(altitudes)

            # Takeoff from first fix or takeoff_fix if available
            if hasattr(flight, "takeoff_fix") and flight.takeoff_fix is not None:
                to_fix = flight.takeoff_fix
            elif fixes:
                to_fix = fixes[0]
            else:
                to_fix = None

            if to_fix is not None:
                takeoff_time = _format_time_of_day(getattr(to_fix, "rawtime", None))
                # Use GNSS altitude for takeoff (more accurate)
                to_alt = getattr(to_fix, "gnss_alt", None)
                if to_alt is not None:
                    takeoff_altitude = float(to_alt)

                takeoff_latitude = getattr(to_fix, "lat", None)
                takeoff_longitude = getattr(to_fix, "lon", None)

            # Landing from last fix
            if fixes and len(fixes) > 0:
                landing_fix = fixes[-1]
                landing_time = _format_time_of_day(getattr(landing_fix, "rawtime", None))
                # Use GNSS altitude for landing (more accurate)
                land_alt = getattr(landing_fix, "gnss_alt", None)
                if land_alt is not None:
                    landing_altitude = float(land_alt)

            # Calculate duration as difference between landing and takeoff times
            if fixes and len(fixes) > 1:
                takeoff_raw = getattr(fixes[0], "rawtime", None)
                landing_raw = getattr(fixes[-1], "rawtime", None)
                takeoff_secs = _raw_time_to_seconds(takeoff_raw)
                landing_secs = _raw_time_to_seconds(landing_raw)
                if takeoff_secs is not None and landing_secs is not None:
                    duration_seconds = landing_secs - takeoff_secs
                    if duration_seconds < 0:
                        # Handle case where flight crosses midnight
                        duration_seconds += 24 * 3600

            # Calculate altitude gain as max - min (from lowest point in flight)
            if max_altitude is not None and min_altitude is not None:
                max_altitude_gain = max_altitude - min_altitude
        except Exception:
            pass

        takeoff_site = (
            _extract_header_value(file_path, "HOSITSite")
            or _extract_header_value(file_path, "HOSIT")
        )
        if not takeoff_site:
            takeoff_site = _guess_takeoff_site(takeoff_latitude, takeoff_longitude)

        date_value = flight_date.isoformat() if flight_date else None
        if date_value and takeoff_time:
            # preserve date/time string as YYYY-MM-DD HH:MM
            date_value = f"{date_value} {takeoff_time[:5]}"

        return {
            "filename": file_path.name,
            "date": date_value,
            "pilot": pilot_name,
            "glider": getattr(flight, "glider_type", ""),
            "igc_file": str(file_path),
            "duration": _format_duration(duration_seconds),
            "distance_km": distance_km if distance_km is not None else 0.0,
            "max_altitude": max_altitude,
            "takeoff_site": takeoff_site,
            "takeoff_time": takeoff_time,
            "takeoff_altitude": takeoff_altitude,
            "takeoff_latitude": takeoff_latitude,
            "takeoff_longitude": takeoff_longitude,
            "landing_time": landing_time,
            "landing_altitude": landing_altitude,
            "max_altitude_gain": max_altitude_gain,
            "thermalling_height_gain": thermalling_height_gain,
            "notes": "; ".join(flight.notes) if getattr(flight, "notes", None) else "",
        }

    if igc_parser is not None:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            raw = f.read()

        parsed = igc_parser.parse_igc_str(raw)
        # igc_parser output may vary; adapt to known keys
        takeoff_site = _extract_header_value(file_path, "HOSITSite") or _extract_header_value(file_path, "HOSIT")

        return {
            "filename": file_path.name,
            "date": getattr(parsed, "date", None),
            "pilot": pilot_name or getattr(parsed, "pilot", ""),
            "glider": getattr(parsed, "glider", ""),
            "igc_file": str(file_path),
            "duration": None,
            "distance_km": None,
            "max_altitude": None,
            "takeoff_site": takeoff_site,
            "takeoff_time": None,
            "takeoff_altitude": None,
            "takeoff_latitude": None,
            "takeoff_longitude": None,
            "landing_time": None,
            "landing_altitude": None,
            "max_altitude_gain": None,
            "thermalling_height_gain": None,
            "notes": "",
        }

    raise ImportError("No IGC parser installed. Install `libigc` or `igc-parser`.")
