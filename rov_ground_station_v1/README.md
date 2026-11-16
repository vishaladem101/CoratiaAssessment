# ROV Telemetry Ground Station (Dam Inspection Mission Control)

A native cross-platform desktop application built with **Python & PySide6 (Qt)** simulating an underwater inspection ROV deployed at **Nagarjuna Sagar Dam Reservoir**.

Developed for the **Coratia Technologies Software Internship Technical Assessment**.

---

## 1. Quick Start: How to Run the Application

Run the application according to your operating system:

### 🪟 Windows
* **One-Click Launch:** Double-click `scripts\run_windows.bat`
* **Or via Command Prompt / PowerShell:**
  ```cmd
  python -m venv venv
  venv\Scripts\activate
  pip install -r scripts\requirements.txt
  python main.py
  ```

### 🐧 Ubuntu / Linux
* **One-Click Launch:** Run the launch script in your terminal:
  ```bash
  ./scripts/run_linux.sh
  ```
* **Or via Terminal directly:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  pip install -r scripts/requirements.txt
  python3 main.py
  ```
*(Note: If you have the pre-compiled binary, you can also double-click `scripts/ROV_Ground_Station.desktop` or launch `./dist/ROVGroundStation/ROVGroundStation` directly).*

### 🍏 macOS
* **One-Click Launch:** Double-click `scripts/run_mac.command`
* **Or via Terminal directly:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  pip install -r scripts/requirements.txt
  python3 main.py
  ```

---

## 2. Pilot Controls (Keyboard & Joystick)

Once the station opens, click the red **DISARMED** button in the top bar to **ARM** thrusters, then drive using keyboard or plug-and-play USB gamepad / joystick:

| Motion | Keyboard Key | Gamepad / Joystick | Real-World ROV Analogy |
| :--- | :--- | :--- | :--- |
| **Surge Forward / Back** | **Up / Down Arrow** | **Left Stick (Y-axis)** | Forward/Reverse thrusters |
| **Strafe Left / Right** | **Left / Right Arrow** | **Left Stick (X-axis)** | Lateral strafe thrusters |
| **Dive / Surface** | **S / W** | **Right Stick (Y-axis)** | Vertical heave thrusters |
| **Turn Left / Right** | **A / D** | **Right Stick (X-axis)** | Differential yaw torque |
| **Arm / Disarm Toggle** | **Top Bar Button** | **Button A / Cross** | Safety ignition lock |
| **Manual Override** | **🕹️ MANUAL Button**| **Button B / Circle**| Autopilot release |

---

## 3. Key Features

1. **Subsea Water Column Cross-Section (Live 2D Ocean View):**
   - Live visual rendering of surface waves and **Surface Support Boat (GPS Anchor)** floating at 0m.
   - An **umbilical tether cable** connects the surface boat to the inspection ROV.
   - Dynamic auto-scaling depth ruler that smoothly adjusts from shallow surface to deep reservoir floor (100m+).
   - Real-time forward headlights beaming through the water column.

2. **Depth-vs-Time Real-Time Chart:**
   - Hardware-accelerated `pyqtgraph` inverted depth chart (0m at surface, diving downward).
   - Marked with dashed cyan **Surface (0m)** reference line and dynamic gold **Target Depth** setpoint line.
   - Standard SI time axis permanently locked in seconds (`s`).

3. **High-Resolution Satellite Surface Map:**
   - Positioned directly over **Nagarjuna Sagar Dam Reservoir** (`16.579554° N, 79.312759° E`).
   - 100% offline pre-cached satellite tiles + dynamic online fallback for global satellite & OSM streaming layers.
   - Displays real-time GPS coordinates, compass heading, and drift vectors for both the boat and the ROV.

4. **Multi-Axis Closed-Loop Autopilot:**
   - Independent proportional-derivative (PD) controllers for Depth Hold and Heading Hold.
   - Supports simultaneous dual hold (`DEPTH & HDG HOLD`) with smooth disturbance rejection.
   - Smooth snap-to-current setpoints on mode selection and direct manual keyboard/spinbox overrides.

5. **Simulated Water Current (Hydrodynamic Environmental Drift):**
   - Implements realistic fluid drag physics relative to moving water currents.
   - Selectable speed presets: `Calm (0.0 m/s)`, `Mild (0.3 m/s)`, `Moderate (0.7 m/s)`, and `Strong (1.2 m/s)`.
   - Compass flow direction selector (`East (90°)`, `South-East (135° Spillway)`, `South (180°)`, `West (270°)`, and `North (0°)`).
   - Optional **Spillway Downdraft (0.25 m/s suction)** demonstrating active heave thruster compensation during Depth Hold.

6. **Safety & Power Systems:**
   - Safety Arm/Disarm interlock: Thrusters are strictly locked to zero thrust when disarmed.
   - Disarm alert banner across the cockpit.
   - 1.0-second inactivity watchdog that neutralizes thrust when manual controls are released.
   - Real-world **18.5V–19V (5S Li-ion / NMC)** battery simulation with dynamic load-based discharge and multi-stage color health indicators.

7. **USB Gamepad & Joystick Support (Requirement 4):**
   - Plug-and-play controller detection (Linux `/dev/input/js*` and Windows gamepad APIs).
   - Dual analog stick control (Left stick: surge/sway; Right stick: heave/yaw) with deadzone drift filtering.

---

## 4. System Architecture (Model-View-Controller / MVC)

The project adheres to the standard desktop **MVC (Model-View-Controller)** architectural pattern, cleanly separating physical simulation from presentation graphics:

* **Model (`src/rov_simulator.py` & `src/config.py`):**
  - Manages the internal physical state of the ROV: 3D position (surge, sway, depth), orientation (yaw heading, pitch, roll), speeds, and 5S battery voltage.
  - Implements the physical water current disturbance model and closed-loop proportional (P) autopilot controllers for automated depth and heading hold.
  - Pure Python, headless, and independent of any GUI libraries.

* **View (`src/ui_dashboard.py` & `assets/map_view.html`):**
  - Custom light-blue frameless title bar with native window dragging and edge-resizing.
  - 2D Subsea Water Column Cross-Section: Live visual rendering of the boat, tether, and illuminated ROV.
  - Real-time Depth vs. Time plot using hardware-accelerated `pyqtgraph`.
  - Offline-first Leaflet Satellite and Street Map centered at Nagarjuna Sagar Reservoir.
  - Thruster power load gauges and live physical speedometers.

* **Controller (`main.py` & event handlers in `src/ui_dashboard.py`):**
  - Runs a synchronized 20 Hz (50 ms) event loop.
  - Captures continuous pilot keyboard inputs and translates them into normalized thrust commands for the Model.
  - Periodically reads the latest telemetry from the Model and pushes updates into the View widgets.

---

## 5. Project Structure

The project maintains an uncluttered root directory, keeping only the application entrypoint and documentation at the top level:

```
rov_ground_station_v1/
├── assets/                     # Graphical assets & offline map libraries
│   ├── rov_icon.png            # Window & desktop launcher icon
│   ├── down_arrow.svg          # Custom vector dropdown chevron
│   ├── map_view.html           # Leaflet Dam Reservoir Satellite & Street map
│   ├── leaflet.js              # Bundled offline Leaflet JavaScript
│   ├── leaflet.css             # Bundled Leaflet stylesheet
│   └── tiles/                  # Pre-cached 100% offline map tiles (Satellite & Street)
├── src/                        # Core Application Source Code (MVC)
│   ├── __init__.py
│   ├── config.py               # Constants, hydrodynamics, 5S battery, reservoir GPS
│   ├── rov_simulator.py        # [Model] Physics, kinematics & PD-controllers
│   ├── joystick_controller.py  # USB gamepad & joystick input processor
│   ├── ui_dashboard.py         # [View] Backward-compatibility re-export wrapper
│   └── view/                   # [View Package] Modular responsive UI components
│       ├── __init__.py         # View module exports
│       ├── dashboard.py        # Master window shell & 20 Hz telemetry dispatch
│       ├── title_bar.py        # Maritime blue frameless window title bar
│       ├── top_bar.py          # 2-Tier responsive command ribbon & battery gauge
│       ├── left_panel.py       # Telemetry table, thrusters, current & help box
│       ├── right_panel.py      # 2D subsea column, depth plot & satellite map
│       ├── custom_widgets.py   # SubseaWaterColumnWidget & CleanSpinBox
│       └── resources.py        # Asset path resolution utility
├── scripts/                    # Launchers & Desktop packaging automation
│   ├── run_linux.sh            # 1-Click launcher for Ubuntu / Linux
│   ├── run_windows.bat         # 1-Click launcher for Windows
│   ├── run_mac.command         # 1-Click launcher for macOS
│   ├── build_desktop_app.py    # Desktop packaging build script (for developers)
│   ├── download_offline_tiles.py # Tile downloader for offline dam reservoir coverage
│   ├── ROVGroundStation.spec   # PyInstaller cross-platform bundle specification
│   ├── ROV_Ground_Station.desktop # Linux desktop shortcut
│   └── requirements.txt        # Minimal cross-platform dependencies
├── main.py                     # [Controller] 20 Hz loop entrypoint
└── README.md                   # Project documentation & architecture overview
```

---

## 6. Compiling Desktop Executables (Developers)

To compile the source code into a standalone desktop binary (which can be distributed to end-users without requiring Python installed):

```bash
python scripts/build_desktop_app.py
```

* **On Windows:** Produces a standalone `dist\ROVGroundStation\ROVGroundStation.exe`.
* **On Linux (Ubuntu):** Produces a standalone `dist/ROVGroundStation/ROVGroundStation` executable.
* **On macOS:** Produces a standalone `dist/ROVGroundStation/ROVGroundStation.app` bundle.

---

## 7. AI Disclosure
* **Tool Used:** Antigravity (Powered by Gemini)
* **Usage:** Assisted in designing the modular MVC architecture (separating backend physics from presentation GUI), implementing the 2D subsea water column view using `QPainter`, configuring the satellite basemap, and generating cross-platform launchers and build specifications. All logic and math were reviewed and verified by the candidate.
