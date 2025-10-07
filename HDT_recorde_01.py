import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
import serial
import serial.tools.list_ports
import pynmea2
import threading
import csv
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Globals
ser = None
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

            except Exception as e:
                print("Error:", e)


# ------------------ Dashboard ------------------
def start_dashboard():
    setup_win.destroy()
    dashboard = tk.Tk()
    dashboard.title("Vessel Dashboard")
    dashboard.configure(bg="white")
    dashboard.geometry("1000x700")

    # Labels
    vessel_lbl = tk.Label(dashboard, text=f"Vessel: {vessel_name}", font=("Segoe UI", 18, "bold"), bg="white")
    vessel_lbl.pack(pady=10)

    heading_lbl = tk.Label(dashboard, text="Heading: ---°", font=("Segoe UI", 16), bg="white")
    heading_lbl.pack(pady=5)

    gps_lbl = tk.Label(dashboard, text="GPS: Lat ---, Lon ---", font=("Segoe UI", 14), bg="white")
    gps_lbl.pack(pady=5)

    # Matplotlib Graph
    fig, ax = plt.subplots()
    line, = ax.plot([], [], 'b-o')
    ax.set_title("Heading Plot")
    ax.set_xlabel("Time")
    ax.set_ylabel("Heading (°)")

    canvas = FigureCanvasTkAgg(fig, master=dashboard)
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # Control Buttons (Windows style)
    controls = tk.Frame(dashboard, bg="white")
    controls.pack(pady=10)

    btn_style = {"font": ("Segoe UI", 12), "width": 12, "relief": "raised", "bd": 1}

    pause_btn = tk.Button(controls, text="Pause", **btn_style)
    play_btn = tk.Button(controls, text="Play", state="disabled", **btn_style)
    stop_btn = tk.Button(controls, text="Stop", **btn_style)
    setup_btn = tk.Button(controls, text="Setup", **btn_style)
    exit_btn = tk.Button(controls, text="Exit", **btn_style)

    pause_btn.grid(row=0, column=0, padx=10)
    play_btn.grid(row=0, column=1, padx=10)
    stop_btn.grid(row=0, column=2, padx=10)
    setup_btn.grid(row=0, column=3, padx=10)
    exit_btn.grid(row=0, column=4, padx=10)

    # Button logic
    def do_pause():
        global paused
        paused = True
        pause_btn.config(state="disabled")
        play_btn.config(state="normal")

    def do_play():
        global paused
        paused = False
        play_btn.config(state="disabled")
        pause_btn.config(state="normal")
        stop_btn.config(state="normal")

  
    def do_stop():
        global stopped, paused
        stopped = True   # stop recording
        paused = True    # also pause updates
        stop_btn.config(state="disabled")
        pause_btn.config(state="disabled")
        play_btn.config(state="normal")


    def go_setup():
        global stopped, paused

        stopped = True
        paused = True
        if ser and ser.is_open:
            ser.close()
        dashboard.destroy()
        main()

    def do_exit():
        if ser and ser.is_open:
            ser.close()
        dashboard.destroy()

    pause_btn.config(command=do_pause)
    play_btn.config(command=do_play)
    stop_btn.config(command=do_stop)
    setup_btn.config(command=go_setup)
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

        dashboard.after(2000, update_ui)

    update_ui()
    dashboard.mainloop()


# ------------------ Setup Window ------------------
def main():
    global setup_win, ser, vessel_name, com_port, baudrate, heading_file, stopped, paused

    setup_win = tk.Tk()
    setup_win.title("Setup Vessel")
    setup_win.configure(bg="white")
    setup_win.geometry("400x400")

    tk.Label(setup_win, text="Vessel Name:", font=("Segoe UI", 12, "bold"), bg="white").pack(pady=5)
    vessel_entry = tk.Entry(setup_win, font=("Segoe UI", 12))
    vessel_entry.pack(pady=5)

    tk.Label(setup_win, text="COM Port:", font=("Segoe UI", 12, "bold"), bg="white").pack(pady=5)
    ports = [port.device for port in serial.tools.list_ports.comports()]
    com_var = tk.StringVar(value=ports[0] if ports else "")
    com_menu = ttk.Combobox(setup_win, textvariable=com_var, values=ports, state="readonly", font=("Segoe UI", 12))
    com_menu.pack(pady=5)

    tk.Label(setup_win, text="Baudrate:", font=("Segoe UI", 12, "bold"), bg="white").pack(pady=5)
    baudrates = ["4800", "9600", "19200", "38400", "57600", "115200"]
    baud_var = tk.StringVar(value="4800")
    baud_menu = ttk.Combobox(setup_win, textvariable=baud_var, values=baudrates, state="readonly", font=("Segoe UI", 12))
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
        start_dashboard()

    tk.Button(setup_win, text="Start", command=start, font=("Segoe UI", 12), width=12, relief="raised", bd=1).pack(pady=20)
    setup_win.mainloop()


if __name__ == "__main__":
    main()
