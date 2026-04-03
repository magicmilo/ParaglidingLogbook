import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from logbook.db import Database
from logbook.file_scanner import import_new_flights


def _parse_duration(duration_str):
    """Parse HH:MM:SS format to total seconds."""
    if not duration_str or duration_str == "":
        return 0
    try:
        parts = duration_str.split(":")
        if len(parts) == 3:
            h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
            return h * 3600 + m * 60 + s
    except (ValueError, IndexError):
        pass
    return 0


def _format_total_duration(total_seconds):
    """Format total seconds to 'dd days hh hours mm minutes ss seconds'."""
    days = total_seconds // 86400
    remainder = total_seconds % 86400
    hours = remainder // 3600
    remainder = remainder % 3600
    minutes = remainder // 60
    seconds = remainder % 60
    return f"{days}d {hours}h {minutes}m {seconds}s"


def _parse_dayhourminsec(value):
    """Parse dd:hh:mm:ss into total seconds."""
    if not value:
        return 0
    parts = value.strip().split(":")
    if len(parts) != 4:
        return 0
    try:
        days, hours, mins, secs = (int(p) for p in parts)
        if days < 0 or hours < 0 or mins < 0 or secs < 0:
            return 0
        return days * 86400 + hours * 3600 + mins * 60 + secs
    except ValueError:
        return 0


def _format_dayhourminsec(total_seconds):
    """Format total seconds as dd:hh:mm:ss."""
    total_seconds = max(0, int(total_seconds))
    days = total_seconds // 86400
    remainder = total_seconds % 86400
    hours = remainder // 3600
    remainder %= 3600
    minutes = remainder // 60
    seconds = remainder % 60
    return f"{days:02d}:{hours:02d}:{minutes:02d}:{seconds:02d}"


class LogbookGUI:
    """GUI application for paragliding logbook."""

    def __init__(self, root, db):
        self.root = root
        self.db = db
        self.root.title("Paragliding Logbook")
        self.root.geometry("1000x600")

        self.current_pilot = self.db.get_default_pilot() or ""

        self.unrecorded_flights_var = tk.StringVar(value=self.db.get_setting("unrecorded_flights_count") or "0")
        self.unrecorded_flight_time_var = tk.StringVar(value=self.db.get_setting("unrecorded_flight_time") or "0:00:00:00")

        self.setup_ui()
        self.refresh_table()

    def setup_ui(self):
        """Setup the GUI layout."""
        # Top button frame with left and right sections
        button_frame = ttk.Frame(self.root, padding="8")
        button_frame.pack(fill="x", padx=8, pady=8)

        # Left side: buttons and pilot label
        left_frame = ttk.Frame(button_frame)
        left_frame.pack(side="left", anchor="n")

        # First row: main control buttons
        buttons_row = ttk.Frame(left_frame)
        buttons_row.pack(side="top", anchor="w")

        import_btn = ttk.Button(
            buttons_row,
            text="Import New Data",
            command=self.on_import_new_data,
        )
        import_btn.pack(side="left", padx=4)

        refresh_btn = ttk.Button(buttons_row, text="Refresh", command=self.refresh_table)
        refresh_btn.pack(side="left", padx=4)

        self.current_pilot_label = ttk.Label(buttons_row, text=f"Pilot: {self.current_pilot or 'None'}")
        self.current_pilot_label.pack(side="left", padx=4)

        clear_all_btn = ttk.Button(buttons_row, text="Clear All Data", command=self.on_clear_all_data)
        clear_all_btn.pack(side="left", padx=4)

        # Second row: unrecorded fields
        unrecorded_frame = ttk.Frame(left_frame, padding="4")
        unrecorded_frame.pack(side="top", anchor="w", pady=(4, 0))

        ttk.Label(unrecorded_frame, text="Unrecorded flights:").pack(side="left", padx=(0,4))
        self.unrecorded_flights_entry = ttk.Entry(unrecorded_frame, width=6, textvariable=self.unrecorded_flights_var)
        self.unrecorded_flights_entry.pack(side="left", padx=(0,8))

        ttk.Label(unrecorded_frame, text="Unrecorded flight time (dd:hh:mm:ss):").pack(side="left", padx=(0,4))
        self.unrecorded_flight_time_entry = ttk.Entry(unrecorded_frame, width=12, textvariable=self.unrecorded_flight_time_var)
        self.unrecorded_flight_time_entry.pack(side="left", padx=(0,8))

        self.unrecorded_flights_entry.bind("<FocusOut>", lambda e: self._save_unrecorded_settings())
        self.unrecorded_flight_time_entry.bind("<FocusOut>", lambda e: self._save_unrecorded_settings())
        self.unrecorded_flight_time_entry.bind("<Return>", lambda e: self._save_unrecorded_settings())

        # Right side: statistics box (outer container)
        stats_frame = tk.Frame(button_frame, relief="solid", bd=1)
        stats_frame.pack(side="right", fill="x", padx=4)

        # Inner frame 1: Current stats (light grey)
        stats_inner_frame = tk.Frame(stats_frame, bg="#d3d3d3", relief="solid", bd=0)
        stats_inner_frame.pack(fill="x")

        # Total flight time
        total_label = tk.Label(
            stats_inner_frame,
            text="Total Flight Time:",
            bg="#d3d3d3",
            font=("TkDefaultFont", 9, "bold")
        )
        total_label.pack(side="left", padx=8, pady=4)

        self.total_time_value = tk.Label(
            stats_inner_frame,
            text="0d 0h 0m 0s",
            bg="#d3d3d3",
            font=("TkDefaultFont", 9)
        )
        self.total_time_value.pack(side="left", padx=8, pady=4)

        # Separator
        sep = tk.Label(stats_inner_frame, text="|", bg="#d3d3d3")
        sep.pack(side="left", padx=4, pady=4)

        # Max altitude
        max_alt_label = tk.Label(
            stats_inner_frame,
            text="Maximum Altitude:",
            bg="#d3d3d3",
            font=("TkDefaultFont", 9, "bold")
        )
        max_alt_label.pack(side="left", padx=8, pady=4)

        self.max_altitude_value = tk.Label(
            stats_inner_frame,
            text="0 m",
            bg="#d3d3d3",
            font=("TkDefaultFont", 9)
        )
        self.max_altitude_value.pack(side="left", padx=8, pady=4)

        # Inner frame 2: Pilot Tasks (darker grey)
        pilot_tasks_frame = tk.Frame(stats_frame, bg="#a9a9a9", relief="solid", bd=0)
        pilot_tasks_frame.pack(fill="x", pady=(4, 0))

        # Pilot Tasks title
        tasks_title = tk.Label(
            pilot_tasks_frame,
            text="Pilot Tasks",
            bg="#a9a9a9",
            font=("TkDefaultFont", 9, "bold")
        )
        tasks_title.pack(anchor="w", padx=8, pady=(4, 2))

        # Thermal gains field
        therm_label = tk.Label(
            pilot_tasks_frame,
            text="Therm 1000ft+ count:",
            bg="#a9a9a9",
            font=("TkDefaultFont", 9, "bold")
        )
        therm_label.pack(side="left", padx=8, pady=4)

        self.therm_count_value = tk.Label(
            pilot_tasks_frame,
            text="0",
            bg="#a9a9a9",
            font=("TkDefaultFont", 9)
        )
        self.therm_count_value.pack(side="left", padx=8, pady=4)

        # Main content frame with Treeview
        content_frame = ttk.Frame(self.root, padding="8")
        content_frame.pack(fill="both", expand=True, padx=8, pady=8)

        # Table with scrollbars
        tree_frame = ttk.Frame(content_frame)
        tree_frame.pack(fill="both", expand=True)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")

        # Define columns: show key fields only, hide filename
        columns = (
            "date",
            "pilot",
            "glider",
            "takeoff_site",
            "takeoff_time",
            "takeoff_altitude",
            "landing_time",
            "landing_altitude",
            "duration",
            "distance_km",
            "max_altitude",
            "max_altitude_gain",
        )
        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
        )
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        # Configure columns
        self.tree.heading("date", text="Date")
        self.tree.column("date", width=130)

        self.tree.heading("pilot", text="Pilot")
        self.tree.column("pilot", width=100)

        self.tree.heading("glider", text="Glider")
        self.tree.column("glider", width=110)

        self.tree.heading("takeoff_site", text="Takeoff Site")
        self.tree.column("takeoff_site", width=90)

        self.tree.heading("takeoff_time", text="Takeoff Time")
        self.tree.column("takeoff_time", width=75)

        self.tree.heading("takeoff_altitude", text="Takeoff Alt (m)")
        self.tree.column("takeoff_altitude", width=75)

        self.tree.heading("landing_time", text="Landing Time")
        self.tree.column("landing_time", width=75)

        self.tree.heading("landing_altitude", text="Landing Alt (m)")
        self.tree.column("landing_altitude", width=75)

        self.tree.heading("duration", text="Duration")
        self.tree.column("duration", width=75)

        self.tree.heading("distance_km", text="Distance (km)")
        self.tree.column("distance_km", width=70)

        self.tree.heading("max_altitude", text="Max Alt (m)")
        self.tree.column("max_altitude", width=75)

        self.tree.heading("max_altitude_gain", text="Alt Gain (m)")
        self.tree.column("max_altitude_gain", width=80)

        self.tree.pack(fill="both", expand=True)

        # Bind selection to show details
        self.tree.bind("<<TreeviewSelect>>", self.on_select_flight)

        # Details frame (collapsible sections)
        self.details_frame = ttk.LabelFrame(
            content_frame, text="Flight Details", padding="8"
        )
        self.details_frame.pack(fill="x", pady=8)

        # Create scrollable frame for details
        details_scroll = ttk.Frame(self.details_frame)
        details_scroll.pack(fill="x")

        self.details_text = tk.Text(
            details_scroll, height=8, width=80, state="disabled", wrap="word"
        )
        self.details_text.pack(fill="both", expand=True)

    def refresh_table(self):
        """Refresh the flights table."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Load flights from DB
        flights = self.db.get_flights()
        
        # Calculate statistics
        total_seconds = 0
        max_altitude = 0
        therm_1000ft_count = 0
        therm_1000ft_threshold = 304.8  # 1000 feet in meters
        
        for flight in flights:
            # Sum total flight time
            if flight.duration:
                total_seconds += _parse_duration(flight.duration)
            # Track maximum altitude
            if flight.max_altitude and flight.max_altitude > max_altitude:
                max_altitude = flight.max_altitude
            # Count flights with thermal gains exceeding 1000 feet
            if flight.thermalling_height_gain and flight.thermalling_height_gain > therm_1000ft_threshold:
                therm_1000ft_count += 1

        # Add unrecorded flight time as extra
        unrecorded_time_seconds = _parse_dayhourminsec(self.unrecorded_flight_time_var.get())
        total_seconds += unrecorded_time_seconds

        # Update stats labels
        self.total_time_value.config(text=_format_total_duration(total_seconds))
        self.max_altitude_value.config(text=f"{max_altitude:.0f} m" if max_altitude > 0 else "0 m")
        self.therm_count_value.config(text=str(therm_1000ft_count))
        
        # Populate table
        for flight in flights:
            values = (
                flight.date or "",
                flight.pilot or "",
                flight.glider or "",
                flight.takeoff_site or "",
                flight.takeoff_time or "",
                f"{flight.takeoff_altitude:.0f}" if flight.takeoff_altitude else "",
                flight.landing_time or "",
                f"{flight.landing_altitude:.0f}" if flight.landing_altitude else "",
                flight.duration or "",
                f"{flight.distance_km:.2f}" if flight.distance_km else "",
                f"{flight.max_altitude:.0f}" if flight.max_altitude else "",
                f"{flight.max_altitude_gain:.0f}" if flight.max_altitude_gain else "",
            )
            self.tree.insert("", "end", values=values)

    def _save_unrecorded_settings(self):
        """Persist unrecorded flight controls to DB and refresh stats."""
        # Validate unrecorded flights count
        try:
            count_value = int(self.unrecorded_flights_var.get())
            if count_value < 0:
                count_value = 0
        except ValueError:
            count_value = 0
        self.unrecorded_flights_var.set(str(count_value))

        # Validate unrecorded time string
        raw_time = self.unrecorded_flight_time_var.get().strip()
        seconds = _parse_dayhourminsec(raw_time)
        self.unrecorded_flight_time_var.set(_format_dayhourminsec(seconds))

        self.db.set_setting("unrecorded_flights_count", str(count_value))
        self.db.set_setting("unrecorded_flight_time", self.unrecorded_flight_time_var.get())

        self.refresh_table()

    def on_select_flight(self, event):
        """Handle flight selection to show details."""
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        index = self.tree.index(item)

        # Get the selected flight from DB
        flights = self.db.get_flights()
        if index < len(flights):
            flight = flights[index]
            self.show_flight_details(flight)

    def show_flight_details(self, flight):
        """Display flight details in the details panel."""
        takeoff_alt = "N/A"
        if flight.takeoff_altitude is not None:
            takeoff_alt = f"{flight.takeoff_altitude:.0f}"

        landing_alt = "N/A"
        if flight.landing_altitude is not None:
            landing_alt = f"{flight.landing_altitude:.0f}"

        distance = "N/A"
        if flight.distance_km is not None:
            distance = f"{flight.distance_km:.2f}"

        max_alt = "N/A"
        if flight.max_altitude is not None:
            max_alt = f"{flight.max_altitude:.0f}"

        max_gain = "N/A"
        if flight.max_altitude_gain is not None:
            max_gain = f"{flight.max_altitude_gain:.0f}"

        details = f"""
BASICS
  Date: {flight.date or 'N/A'}
  Pilot: {flight.pilot or 'N/A'}
  Glider: {flight.glider or 'N/A'}

FLIGHT DATA
  Takeoff Site: {flight.takeoff_site or 'N/A'}
  Takeoff Time: {flight.takeoff_time or 'N/A'}
  Takeoff Altitude: {takeoff_alt} m
  Landing Time: {flight.landing_time or 'N/A'}
  Landing Altitude: {landing_alt} m
  Duration: {flight.duration or 'N/A'}
  Distance: {distance} km
  Max Altitude: {max_alt} m
  Altitude Gain: {max_gain} m

METADATA
  File: {flight.filename}
  Imported: {flight.created_at}
  Notes: {flight.notes or 'N/A'}
"""

        self.details_text.config(state="normal")
        self.details_text.delete("1.0", "end")
        self.details_text.insert("1.0", details)
        self.details_text.config(state="disabled")

    def on_clear_all_data(self):
        """Clear all flight records after confirmation."""
        confirm = messagebox.askyesno(
            "Confirm Clear All",
            "Are you sure you want to delete ALL flight data? This cannot be undone.",
        )
        if not confirm:
            return

        deleted = self.db.delete_all_flights()
        self.refresh_table()
        messagebox.showinfo("All Data Cleared", f"Deleted {deleted} flight(s) from database.")

    def on_import_new_data(self):
        """Import new IGC files from flight_data folder."""
        try:
            count, errors = import_new_flights(self.db, verbose=False)
            
            message = f"Imported {count} new flight(s)."
            if errors:
                message += f"\n\n{len(errors)} error(s):\n" + "\n".join(errors[:5])
                if len(errors) > 5:
                    message += f"\n... and {len(errors) - 5} more"
            
            self.refresh_table()
            messagebox.showinfo("Import Complete", message)
        except Exception as e:
            messagebox.showerror("Import Error", f"Error importing flights: {str(e)}")


def run_gui(db: Database):
    """Launch the GUI application."""
    root = tk.Tk()
    app = LogbookGUI(root, db)
    root.mainloop()
