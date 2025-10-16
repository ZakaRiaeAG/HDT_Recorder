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

# ------------------ Choice Window ------------------
def choice_window():
    global signal_type
    win = tk.Tk()
    win.title("Select Signal Type")
    win.geometry("400x250")
    win.configure(bg="white")

    tk.Label(win, text="Select Signal Source:", font=("Segoe UI", 14, "bold"), bg="white").pack(pady=20)

    signal_var = tk.StringVar(value="NMEA0183")
    tk.Radiobutton(win, text="NMEA0183", variable=signal_var, value="NMEA0183", font=("Segoe UI", 12), bg="white").pack(pady=5)
    tk.Radiobutton(win, text="AIS", variable=signal_var, value="AIS", font=("Segoe UI", 12), bg="white").pack(pady=5)

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
    win.title("Setup Vessel")
    win.geometry("400x400")
    win.configure(bg="white")

    tk.Label(win, text="Vessel Name:", font=("Segoe UI", 12, "bold"), bg="white").pack(pady=5)
    vessel_entry = tk.Entry(win, font=("Segoe UI", 12))
    vessel_entry.pack(pady=5)

    tk.Label(win, text="COM Port:", font=("Segoe UI", 12, "bold"), bg="white").pack(pady=5)
    ports = [port.device for port in serial.tools.list_ports.comports()]
    com_var = tk.StringVar(value=ports[0] if ports else "")
    com_menu = ttk.Combobox(win, textvariable=com_var, values=ports, state="readonly", font=("Segoe UI", 12))
    com_menu.pack(pady=5)

    tk.Label(win, text="Baudrate:", font=("Segoe UI", 12, "bold"), bg="white").pack(pady=5)
    baudrates = ["4800", "9600", "19200", "38400", "57600", "115200"]
    baud_var = tk.StringVar(value="4800")
    baud_menu = ttk.Combobox(win, textvariable=baud_var, values=baudrates, state="readonly", font=("Segoe UI", 12))
    baud_menu.pack(pady=5)

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

    tk.Button(win, text="Start", font=("Segoe UI", 12), width=12, command=start).pack(pady=20)
    win.mainloop()

# ------------------ Dashboard ------------------
def dashboard_window():
    global paused, stopped

    dash = tk.Tk()
    dash.title("Vessel Dashboard")
    dash.geometry("1000x700")
    dash.configure(bg="white")

    # Labels
    vessel_lbl = tk.Label(dash, text=f"Vessel: {vessel_name}", font=("Segoe UI", 18, "bold"), bg="white")
    vessel_lbl.pack(pady=10)
    heading_lbl = tk.Label(dash, text="Heading: ---°", font=("Segoe UI", 16), bg="white")
    heading_lbl.pack(pady=5)
    gps_lbl = tk.Label(dash, text="GPS: Lat ---, Lon ---", font=("Segoe UI", 14), bg="white")
    gps_lbl.pack(pady=5)

    # Matplotlib Graph
    fig, ax = plt.subplots()
    canvas = FigureCanvasTkAgg(fig, master=dash)
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # Buttons
    frame = tk.Frame(dash, bg="white")
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
            ax.plot(times, headings, 'b-o')
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
