import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
import serial
import serial.tools.list_ports
import threading
import csv
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pynmea2
from pyais import decode as ais_decode
import os
from PIL import Image, ImageTk

# ------------------ Globals ------------------
ser = None
signal_type = "NMEA0183"  # default
vessel_name = ""
com_port = ""
baudrate = 4800
heading_file = None
paused = False
stopped = False

heading = 0.0
latitude = None
longitude = None
headings = []
times = []

logo_path = os.path.join(os.path.dirname(__file__), "MackayMarine_Logo.png")

ais_targets = {}  # store AIS info keyed by MMSI

# ------------------ Serial Reader ------------------
def read_serial():
    global heading, latitude, longitude, paused, stopped
    while True:
        if ser and ser.is_open and not paused:
            try:
                line = ser.readline().decode(errors="ignore").strip()
                if not line:
                    continue

                # record raw NMEA only if not stopped
                if not stopped:
                    with open(vessel_name + "_NMEA.csv", "a", newline="") as f:
                        writer = csv.writer(f)
                        writer.writerow([datetime.utcnow().isoformat(), line])

                if signal_type == "NMEA0183":
                    if line.startswith("$HEHDT") or line.startswith("$HEHDG"):
                        msg = pynmea2.parse(line)
                        heading = float(msg.heading)
                        headings.append(heading)
                        times.append(datetime.now())
                        if not stopped:
                            with open(heading_file, "a", newline="") as f:
                                writer = csv.writer(f)
                                writer.writerow([datetime.utcnow().isoformat(), heading])
                    elif line.startswith("$GPRMC") or line.startswith("$GPGGA") or line.startswith("$GPGLL"):
                        msg = pynmea2.parse(line)
                        latitude = msg.latitude
                        longitude = msg.longitude

                elif signal_type == "AIS":
                    if line.startswith("!AIVDO"):
                        try:
                            ais_msg = ais_decode(line)
                            mmsi = ais_msg.mmsi
                            ais_targets[mmsi] = {
                                "MMSI": mmsi,
                                "Vessel": getattr(ais_msg, "shipname", "Unknown"),
                                "Lat": getattr(ais_msg, "lat", None),
                                "Lon": getattr(ais_msg, "lon", None),
                                "Heading": getattr(ais_msg, "heading", None),
                                "COG": getattr(ais_msg, "course_over_ground", None),
                                "Speed": getattr(ais_msg, "speed_over_ground", None)
                            }
                            print(ais_msg)
                            # use first AIS target for dashboard display
                            if ais_targets:
                                first = next(iter(ais_targets.values()))
                                heading = first["Heading"]
                                latitude = first["Lat"]
                                longitude = first["Lon"]
                                print(heading, latitude, longitude)
                                if not stopped:
                                    headings.append(heading)
                                    times.append(datetime.now())
                                    with open(heading_file, "a", newline="") as f:
                                        writer = csv.writer(f)
                                        writer.writerow([datetime.utcnow().isoformat(), heading])
                        except Exception as e:
                            print("AIS decode error:", e)

            except Exception as e:
                print("Serial read error:", e)
# ------------------ Background Logo ------------------
def add_background(window):
    """Set a grey background and place a dynamically resizing logo at the top-right corner."""
    window.configure(bg="#d9d9d9")  # set full background color
    logo_label = tk.Label(window, bg="#d9d9d9", borderwidth=0)
    logo_label.place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=10)

    def resize_logo(event=None):
        try:
            img = Image.open(logo_path)
            # Scale logo dynamically to ~10% of window height
            size = int(window.winfo_height() * 0.1)
            if size < 60:
                size = 60  # minimum size
            resized = img.resize((size + 60, size), Image.LANCZOS)
            logo_img = ImageTk.PhotoImage(resized)
            logo_label.config(image=logo_img)
            logo_label.image = logo_img  # keep reference
        except Exception as e:
            print(f"Warning: Could not resize logo ({e})")

    window.bind("<Configure>", resize_logo)
    resize_logo()  # initial call

# ------------------ Choice Window ------------------
def choice_window():
    global signal_type
    win = tk.Tk()
    add_background(win)
    win.title("Select Signal Type")
    win.geometry("460x320")
    win.configure(bg="#d9d9d9")

    tk.Label(win, text="Select signal source:", anchor="w", font=("Segoe UI", 12), bg="#d9d9d9").pack(fill="x",padx=(10,0), pady=(100, 5))

    signal_var = tk.StringVar(value="NMEA0183")
    tk.Radiobutton(win, text="NMEA0183", variable=signal_var, value="NMEA0183", anchor="w", font=("Segoe UI", 12), bg="#d9d9d9").pack(fill="x", padx=(180, 0), pady=5)
    tk.Radiobutton(win, text="AIS", variable=signal_var, value="AIS", anchor="w", font=("Segoe UI", 12), bg="#d9d9d9").pack(fill="x", padx=(180, 0), pady=5)

    def next_win():
        global signal_type
        signal_type = signal_var.get()
        win.destroy()
        setup_window()

    tk.Button(win, text="Next", font=("Segoe UI", 12), width=12, command=next_win).pack(pady=20)
    win.mainloop()

# ------------------ Setup Window ------------------
def setup_window():
    global ser, vessel_name, com_port, baudrate, heading_file, stopped, paused

    win = tk.Tk()
    add_background(win)
    win.title("Setup Vessel")
    win.geometry("460x360")
    win.configure(bg="#d9d9d9")

    tk.Label(win, text="Vessel Name:", font=("Segoe UI", 12), bg="#d9d9d9").grid(row=0, column=0, padx=10, pady=(100, 10), sticky="w")
    vessel_entry = tk.Entry(win, font=("Segoe UI", 12))
    vessel_entry.grid(row=0, column=1, pady=(100, 10))

    tk.Label(win, text="COM Port:", font=("Segoe UI", 12), bg="#d9d9d9").grid(row=1, column=0, padx=10, sticky="w")
    ports = [port.device for port in serial.tools.list_ports.comports()]
    com_var = tk.StringVar(value=ports[0] if ports else "")
    com_menu = ttk.Combobox(win, textvariable=com_var, values=ports, state="readonly", font=("Segoe UI", 12))
    com_menu.grid(row=1, column=1, padx=10, pady=10)

    tk.Label(win, text="Baudrate:", font=("Segoe UI", 12), bg="#d9d9d9").grid(row=2, column=0, padx=10, pady=10, sticky="w")
    baudrates = ["4800", "9600", "19200", "38400", "57600", "115200"]
    baud_var = tk.StringVar(value="4800")
    baud_menu = ttk.Combobox(win, textvariable=baud_var, values=baudrates, state="readonly", font=("Segoe UI", 12))
    baud_menu.grid(row=2, column=1, padx=10, pady=10)

    def start():
        global ser, vessel_name, com_port, baudrate, heading_file, stopped, paused
        vessel_name = vessel_entry.get()
        com_port = com_var.get()
        baudrate = int(baud_var.get())
        heading_file = vessel_name + "_Heading.csv"
        stopped = False
        paused = False
        ser = serial.Serial(com_port, baudrate=baudrate, timeout=1)
        threading.Thread(target=read_serial, daemon=True).start()
        win.destroy()
        dashboard_window()

    tk.Button(win, text="Start", font=("Segoe UI", 12), width=12, command=start).grid(row=3, column=1, padx=10,pady=10)
    win.mainloop()

# ------------------ Dashboard ------------------
def dashboard_window():
    global paused, stopped

    dash = tk.Tk()
    add_background(dash)
    dash.title("Vessel Dashboard")
    dash.geometry("1000x700")
    dash.configure(bg="#d9d9d9")

    # Labels
    vessel_lbl = tk.Label(dash, text=f"Vessel: {vessel_name}", font=("Segoe UI", 18, "bold"), bg="#d9d9d9")
    vessel_lbl.pack(pady=10)
    heading_lbl = tk.Label(dash, text="Heading: ---°", font=("Segoe UI", 16), bg="#d9d9d9")
    heading_lbl.pack(pady=5)
    gps_lbl = tk.Label(dash, text="GPS: Lat ---, Lon ---", font=("Segoe UI", 14), bg="#d9d9d9")
    gps_lbl.pack(pady=5)

    # Matplotlib Graph
    fig, ax = plt.subplots()
    fig.patch.set_facecolor('#d9d9d9')
    ax.patch.set_facecolor('#d9d9d9')
    canvas = FigureCanvasTkAgg(fig, master=dash)
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # Buttons
    frame = tk.Frame(dash, bg="#d9d9d9")
    frame.pack(pady=10)

    pause_btn = tk.Button(frame, text="Pause", width=12, font=("Segoe UI", 12))
    play_btn = tk.Button(frame, text="Play", width=12, font=("Segoe UI", 12), state="disabled")
    stop_btn = tk.Button(frame, text="Stop", width=12, font=("Segoe UI", 12))
    setup_btn = tk.Button(frame, text="Setup", width=12, font=("Segoe UI", 12))
    exit_btn = tk.Button(frame, text="Exit", width=12, font=("Segoe UI", 12))

    pause_btn.grid(row=0, column=0, padx=5)
    play_btn.grid(row=0, column=1, padx=5)
    stop_btn.grid(row=0, column=2, padx=5)
    setup_btn.grid(row=0, column=3, padx=5)
    exit_btn.grid(row=0, column=4, padx=5)

    def do_pause():
        global paused
        paused = True
        pause_btn.config(state="disabled")
        play_btn.config(state="normal")

    def do_play():
        global paused
        paused = False
        pause_btn.config(state="normal")
        play_btn.config(state="disabled")
        stop_btn.config(state="normal")

    def do_stop():
        global paused, stopped
        stopped = True
        paused = True
        stop_btn.config(state="disabled")
        pause_btn.config(state="disabled")
        play_btn.config(state="normal")

    def do_setup():
        global paused, stopped
        stopped = True
        paused = True
        if ser and ser.is_open:
            ser.close()
        dash.destroy()
        setup_window()

    def do_exit():
        if ser and ser.is_open:
            ser.close()
        dash.destroy()

    pause_btn.config(command=do_pause)
    play_btn.config(command=do_play)
    stop_btn.config(command=do_stop)
    setup_btn.config(command=do_setup)
    exit_btn.config(command=do_exit)

    # Update loop
    def update_ui():
        if not paused and len(headings) > 0:
            heading_lbl.config(text=f"Heading: {headings[-1]:.1f}°")
        if latitude and longitude:
            gps_lbl.config(text=f"GPS: Lat {latitude:.5f}, Lon {longitude:.5f}")

        if len(times) > 0:
            ax.clear()
            ax.set_facecolor('#d9d9d9')
            ax.plot(times, headings, 'b-')
            ax.set_title("Heading Plot")
            ax.set_xlabel("Time")
            ax.set_ylabel("Heading (°)")
            fig.autofmt_xdate()
            canvas.draw()

        dash.after(2000, update_ui)

    update_ui()
    dash.mainloop()

# ------------------ Main ------------------
if __name__ == "__main__":
    choice_window()
