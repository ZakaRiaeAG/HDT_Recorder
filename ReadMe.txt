
# Vessel Heading Display Application

This Python application provides a graphical interface for displaying live data from maritime navigation equipment over a serial (COM) connection.
It supports both NMEA0183 and AIS signal types, decoding messages to show vessel heading, GPS position, and live heading plots in real time.

---

## ⚙️ Features

 Select signal type: `NMEA0183` or `AIS`
 Configure vessel name, COM port, and baud rate
 Live display of:

   Heading (°)
   GPS Latitude & Longitude
   Real-time heading graph
 Controls to:

   Pause / Resume live data
   Stop data logging
   Reopen setup window
   Exit the program safely
 Automatic CSV logging of NMEA sentences and heading data

---

## 🧩 Requirements

Make sure the following Python packages are installed:

```bash
pip install customtkinter pyserial matplotlib pynmea2 pyais
```

> `customtkinter` may require `tkinter` and `ttk` which are usually preinstalled with Python on Windows.

---

## 🖥️ How to Use

### 1. Connect Your Equipment

Connect your NMEA0183 or AIS device to your computer via a serial (COM) port or USB-to-serial adapter.

---

### 2. Run the Program

From the terminal (in the same folder as the script):

```bash
python main.py
```

---

### 3. Step-by-Step Usage

#### 🧭 Step 1 – Choose Signal Type

When the program starts, a small window appears:

 Select NMEA0183 or AIS.
 Click Next.

#### ⚓ Step 2 – Setup Window

In the setup screen:

 Enter your Vessel Name (used for CSV file naming).
 Select your COM Port from the dropdown list.
 Choose the Baudrate (default is `4800` for most NMEA0183 devices).
 Click Start to open the dashboard and begin reading data.

#### 📊 Step 3 – Dashboard Window

The main dashboard displays:

 Vessel name
 Heading in degrees
 GPS coordinates (Lat, Lon)
 A live heading plot updated every few seconds

#### 🎛️ Control Buttons

| Button    | Function                                          |
| --------- | ------------------------------------------------- |
| Pause | Temporarily stop reading from the serial port     |
| Play  | Resume live updates                               |
| Stop  | Stop data recording (pauses updates and logging)  |
| Setup | Return to setup screen (closes serial connection) |
| Exit  | Quit the application safely                       |

---

## 🗂️ Output Files

The app automatically creates two CSV log files in the same directory as the script:

| File Name                  | Description                                      |
| -------------------------- | ------------------------------------------------ |
| `<VesselName>_NMEA.csv`    | Contains all raw NMEA sentences received         |
| `<VesselName>_Heading.csv` | Contains timestamped heading values for plotting |

Example:

```
MyVessel_NMEA.csv
MyVessel_Heading.csv
```

---

## ⚠️ Notes & Tips

 The app requires a valid COM port; otherwise, it won’t start the data reader.
 NMEA0183 mode decodes `$HEHDT`, `$HEHDG`, `$GPRMC`, `$GPGGA`, `$GPGLL` messages.
 AIS mode decodes `!AIVDO` sentences using the `pyais` library.
 If you experience serial errors, check your baud rate and cable connection.

---

## 🧑‍💻 Developer Info

 Language: Python 3.x
 Libraries Used: `customtkinter`, `tkinter`, `ttk`, `serial`, `threading`, `matplotlib`, `pynmea2`, `pyais`
 Author: ZakaRiaeAG
 Version: 1.0

