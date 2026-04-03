import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from logbook.db import Database
from logbook.igc_reader import parse_igc_file


def run_gui(db: Database):
    root = tk.Tk()
    root.title("Paragliding Logbook")
    root.geometry("900x500")

    frame = ttk.Frame(root, padding="8")
    frame.pack(fill="both", expand=True)

    columns = ("id", "date", "pilot", "glider", "igc_file", "duration_minutes", "distance_km")
    tree = ttk.Treeview(frame, columns=columns, show="headings")

    for col in columns:
        tree.heading(col, text=col.replace("_", " ").title())
        tree.column(col, width=120)
    tree.pack(fill="both", expand=True)

    def refresh_table():
        for row in tree.get_children():
            tree.delete(row)
        for flight in db.get_flights():
            tree.insert("", "end", values=(flight["id"], flight["date"], flight["pilot"], flight["glider"], flight["igc_file"], flight["duration_minutes"], flight["distance_km"]))

    def import_igc():
        path = filedialog.askopenfilename(filetypes=[("IGC files", "*.igc"), ("All files", "*")])
        if not path:
            return
        try:
            flight_data = parse_igc_file(Path(path))
            db.add_flight(flight_data)
            refresh_table()
            messagebox.showinfo("Imported", "IGC file imported into database")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    button_frame = ttk.Frame(frame)
    button_frame.pack(fill="x", pady=6)

    import_btn = ttk.Button(button_frame, text="Import IGC", command=import_igc)
    import_btn.pack(side="left", padx=4)

    refresh_btn = ttk.Button(button_frame, text="Refresh", command=refresh_table)
    refresh_btn.pack(side="left", padx=4)

    refresh_table()
    root.mainloop()
