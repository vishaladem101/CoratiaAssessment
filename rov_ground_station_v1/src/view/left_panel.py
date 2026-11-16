"""
Left Telemetry Panel:
  1. Primary Telemetry & Physical Velocities table.
  2. Thruster Power Load progress bars.
  3. Simulated Water Current (hydrodynamic environmental drift).
  4. Pilot Keyboard Controls quick reference table.
Wrapped in an adaptive frameless QScrollArea for small screen heights.
"""
import os
import math
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QGroupBox, QGridLayout,
    QProgressBar, QCheckBox, QListView, QScrollArea, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from src.view.resources import get_resource_path


class LeftTelemetryPanel(QScrollArea):
    """Encapsulates telemetry indicators, thruster load bars, environmental current, and help reference."""
    def __init__(self, simulator, parent=None):
        super().__init__(parent)
        self.sim = simulator
        self.setFocusPolicy(Qt.NoFocus)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                border: none;
                background: #0b111a;
                width: 6px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #1e3a5f;
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: #38bdf8;
            }
        """)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(10)

        # ---------------------------------------------------------
        # 1. Primary Telemetry & Physical Velocities
        # ---------------------------------------------------------
        grp_telemetry = QGroupBox("PRIMARY TELEMETRY & SPEEDS")
        grid = QGridLayout(grp_telemetry)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(7)
        grid.setContentsMargins(12, 10, 12, 10)

        def add_row(r, name, val):
            lbl_name = QLabel(name)
            lbl_name.setStyleSheet("color: #cbd5e1; font-size: 13px; font-weight: 500;")
            grid.addWidget(lbl_name, r, 0)
            lbl = QLabel(val)
            lbl.setFont(QFont("Monospace", 13, QFont.Bold))
            lbl.setStyleSheet("color: #38bdf8; font-size: 14px; font-weight: bold;")
            grid.addWidget(lbl, r, 1, Qt.AlignRight)
            return lbl

        self.lbl_status = add_row(0, "Status:", "DISARMED")
        self.lbl_mode   = add_row(1, "Mode:", "MANUAL")
        self.lbl_depth  = add_row(2, "Depth:", "0.00 m")
        self.lbl_yaw    = add_row(3, "Heading (HDG):", "0.0° (N)")
        self.lbl_pitch  = add_row(4, "Pitch Angle:", "0.0°")
        self.lbl_roll   = add_row(5, "Roll Angle:", "0.0°")

        # Live Physical Speedometers
        self.lbl_surge_speed = add_row(6, "Surge Speed (F/R):", "0.00 m/s")
        self.lbl_sway_speed  = add_row(7, "Sway Speed (L/R):", "0.00 m/s")
        self.lbl_heave_speed = add_row(8, "Dive Speed (D/U):", "0.00 m/s")
        self.lbl_turn_rate   = add_row(9, "Turn Rate (Yaw):", "0.0 °/s")

        layout.addWidget(grp_telemetry)

        # ---------------------------------------------------------
        # 2. Thruster Power Bars (Aligned with QGridLayout)
        # ---------------------------------------------------------
        grp_thrusters = QGroupBox("THRUSTER POWER LOAD")
        thruster_grid = QGridLayout(grp_thrusters)
        thruster_grid.setContentsMargins(12, 10, 12, 10)
        thruster_grid.setHorizontalSpacing(10)
        thruster_grid.setVerticalSpacing(8)
        thruster_grid.setColumnStretch(0, 0)
        thruster_grid.setColumnStretch(1, 1)

        def add_bar(r, txt):
            lbl = QLabel(txt)
            lbl.setStyleSheet("color: #cbd5e1; font-size: 13px; font-weight: bold;")
            lbl.setFixedWidth(110)
            thruster_grid.addWidget(lbl, r, 0, Qt.AlignLeft | Qt.AlignVCenter)

            bar = QProgressBar()
            bar.setRange(-100, 100)
            bar.setValue(0)
            bar.setFormat("%v%")
            bar.setFixedHeight(18)
            bar.setStyleSheet("""
                QProgressBar {
                    background-color: #080d14;
                    border: 1px solid #1e3a5f;
                    border-radius: 4px;
                    text-align: center;
                    color: white;
                    font-size: 12px;
                    font-weight: bold;
                }
                QProgressBar::chunk {
                    background-color: #0284c7;
                }
            """)
            thruster_grid.addWidget(bar, r, 1)
            return bar

        self.bar_surge = add_bar(0, "Surge (↑/↓):")
        self.bar_sway  = add_bar(1, "Sway (←/→):")
        self.bar_heave = add_bar(2, "Heave (S/W):")
        self.bar_yaw   = add_bar(3, "Yaw (A/D):")

        layout.addWidget(grp_thrusters)

        # ---------------------------------------------------------
        # 3. Simulated Water Current (Hydrodynamic Environmental Drift)
        # ---------------------------------------------------------
        grp_current = QGroupBox("🌊 SIMULATED WATER CURRENT")
        cur_layout = QVBoxLayout(grp_current)
        cur_layout.setContentsMargins(12, 10, 12, 10)
        cur_layout.setSpacing(8)

        # Row 1: Presets
        row_presets = QHBoxLayout()
        row_presets.setSpacing(6)
        self.btn_cur_off = QPushButton("Calm")
        self.btn_cur_mild = QPushButton("0.3 m/s")
        self.btn_cur_mod = QPushButton("0.7 m/s")
        self.btn_cur_strong = QPushButton("1.2 m/s")
        self.cur_buttons = [self.btn_cur_off, self.btn_cur_mild, self.btn_cur_mod, self.btn_cur_strong]

        for b in self.cur_buttons:
            b.setFocusPolicy(Qt.NoFocus)
            row_presets.addWidget(b)
        cur_layout.addLayout(row_presets)

        # Row 2: Direction Selector
        row_dir = QHBoxLayout()
        lbl_dir = QLabel("Flow Direction:")
        lbl_dir.setStyleSheet("color: #cbd5e1; font-size: 13px; font-weight: 500;")
        row_dir.addWidget(lbl_dir)
        self.combo_cur_dir = QComboBox()
        self.combo_cur_dir.setView(QListView())
        self.combo_cur_dir.setMaxVisibleItems(8)
        self.combo_cur_dir.setFocusPolicy(Qt.NoFocus)
        self.combo_cur_dir.addItems([
            "East (90°)",
            "South-East (135° Spillway)",
            "South (180°)",
            "West (270°)",
            "North (0°)"
        ])
        arrow_path = get_resource_path("down_arrow.svg").replace("\\", "/")
        self.combo_cur_dir.setStyleSheet(f"""
            QComboBox {{
                combobox-popup: 0;
                background-color: #0b1320;
                color: #38bdf8;
                border: 1px solid #1e3a5f;
                border-radius: 4px;
                padding: 4px 22px 4px 8px;
                font-weight: bold;
                font-size: 12px;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border: none;
            }}
            QComboBox::down-arrow {{
                image: url("{arrow_path}");
                width: 9px;
                height: 5px;
                margin-right: 6px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #0b1320;
                color: #e2e8f0;
                selection-background-color: #0284c7;
                border: 1px solid #0284c7;
                font-size: 12px;
            }}
        """)
        row_dir.addWidget(self.combo_cur_dir)
        cur_layout.addLayout(row_dir)

        # Row 3: Spillway Downdraft Suction
        self.chk_downdraft = QCheckBox("Spillway Downdraft (0.25 m/s suction)")
        self.chk_downdraft.setFocusPolicy(Qt.NoFocus)
        self.chk_downdraft.setStyleSheet("color: #cbd5e1; font-size: 12px; font-weight: 500;")
        cur_layout.addWidget(self.chk_downdraft)

        # Row 4: Status Indicator
        self.lbl_cur_status = QLabel("🌊 Current: CALM (No Drift)")
        self.lbl_cur_status.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 12px;")
        cur_layout.addWidget(self.lbl_cur_status)

        layout.addWidget(grp_current)

        def get_selected_direction():
            txt = self.combo_cur_dir.currentText()
            if "90" in txt:
                return 90.0
            elif "135" in txt:
                return 135.0
            elif "180" in txt:
                return 180.0
            elif "270" in txt:
                return 270.0
            elif "0°" in txt or "000" in txt:
                return 0.0
            return 90.0

        def apply_current(speed, active_btn):
            self.current_preset_speed = speed
            direction = get_selected_direction()
            vertical = 0.25 if self.chk_downdraft.isChecked() else 0.0
            self.sim.set_water_current(speed=speed, direction=direction, vertical=vertical)

            for b in self.cur_buttons:
                b.setStyleSheet("background-color: #1e293b; color: #94a3b8; font-size: 12px; padding: 5px 8px; font-weight: bold;")
            active_btn.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold; font-size: 12px; padding: 5px 8px;")
            win = self.window()
            if win:
                win.setFocus()

        self.current_preset_speed = 0.0
        self.btn_cur_off.clicked.connect(lambda: apply_current(0.0, self.btn_cur_off))
        self.btn_cur_mild.clicked.connect(lambda: apply_current(0.3, self.btn_cur_mild))
        self.btn_cur_mod.clicked.connect(lambda: apply_current(0.7, self.btn_cur_mod))
        self.btn_cur_strong.clicked.connect(lambda: apply_current(1.2, self.btn_cur_strong))

        def on_current_options_changed():
            btn = self.btn_cur_off
            if self.current_preset_speed == 0.3:
                btn = self.btn_cur_mild
            elif self.current_preset_speed == 0.7:
                btn = self.btn_cur_mod
            elif self.current_preset_speed == 1.2:
                btn = self.btn_cur_strong
            apply_current(self.current_preset_speed, btn)

        self.combo_cur_dir.currentIndexChanged.connect(lambda _: on_current_options_changed())
        self.chk_downdraft.toggled.connect(lambda _: on_current_options_changed())

        # Set default styling for Calm
        self.btn_cur_off.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold; font-size: 12px; padding: 5px 8px;")
        for b in (self.btn_cur_mild, self.btn_cur_mod, self.btn_cur_strong):
            b.setStyleSheet("background-color: #1e293b; color: #94a3b8; font-size: 12px; padding: 5px 8px; font-weight: bold;")

        # ---------------------------------------------------------
        # 4. Pilot Controls Help Box
        # ---------------------------------------------------------
        grp_help = QGroupBox("PILOT KEYBOARD CONTROLS")
        hl = QVBoxLayout(grp_help)
        hl.setContentsMargins(12, 10, 12, 10)
        help_text = (
            "<table width='100%' style='color:#cbd5e1; font-size:13px; line-height:170%;'>"
            "<tr><td><b>Forward / Back:</b></td><td align='right'><b style='color:#38bdf8'>Up / Down Arrow</b></td></tr>"
            "<tr><td><b>Strafe Left / Right:</b></td><td align='right'><b style='color:#38bdf8'>Left / Right Arrow</b></td></tr>"
            "<tr><td><b>Dive / Surface:</b></td><td align='right'><b style='color:#38bdf8'>S / W</b></td></tr>"
            "<tr><td><b>Turn Left / Right:</b></td><td align='right'><b style='color:#38bdf8'>A / D</b></td></tr>"
            "</table>"
        )
        lbl_h = QLabel(help_text)
        lbl_h.setTextFormat(Qt.RichText)
        hl.addWidget(lbl_h)
        layout.addWidget(grp_help)

        layout.addStretch()
        self.setWidget(container)

    def update_telemetry(self, telemetry):
        """Updates numerical readings, speeds, thruster load bars, and environmental drift status."""
        is_armed = telemetry["armed"]
        self.lbl_status.setText("ARMED" if is_armed else "DISARMED")
        self.lbl_status.setStyleSheet("color: #4ade80; font-size: 14px; font-weight: bold;" if is_armed else "color: #ef4444; font-size: 14px; font-weight: bold;")

        mode_str = telemetry["mode"]
        self.lbl_mode.setText(f" {mode_str} ")
        if mode_str == "MANUAL":
            self.lbl_mode.setStyleSheet("background-color: #0369a1; color: white; border-radius: 4px; padding: 2px 6px; font-size: 13px; font-weight: bold;")
        elif mode_str == "DEPTH_HOLD":
            self.lbl_mode.setStyleSheet("background-color: #b45309; color: white; border-radius: 4px; padding: 2px 6px; font-size: 13px; font-weight: bold;")
        elif mode_str == "HEADING_HOLD":
            self.lbl_mode.setStyleSheet("background-color: #0e7490; color: white; border-radius: 4px; padding: 2px 6px; font-size: 13px; font-weight: bold;")
        else:  # DEPTH & HDG HOLD
            self.lbl_mode.setStyleSheet("background-color: #047857; color: white; border-radius: 4px; padding: 2px 6px; font-size: 13px; font-weight: bold;")

        depth = telemetry["depth"]
        yaw = telemetry["yaw"]
        self.lbl_depth.setText(f"{depth:.2f} m")

        cardinals = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        idx = int((yaw + 22.5) % 360 // 45)
        self.lbl_yaw.setText(f"{yaw:.1f}° ({cardinals[idx]})")

        self.lbl_pitch.setText(f"{telemetry['pitch']:+.1f}°")
        self.lbl_roll.setText(f"{telemetry['roll']:+.1f}°")

        # Physical Speedometers
        surge_spd = telemetry.get("speed_surge", 0.0)
        sway_spd  = telemetry.get("speed_sway", 0.0)
        heave_spd = telemetry.get("speed_heave", 0.0)
        yaw_spd   = telemetry.get("speed_yaw", 0.0)

        self.lbl_surge_speed.setText(f"{surge_spd:+.2f} m/s")
        self.lbl_sway_speed.setText(f"{sway_spd:+.2f} m/s")
        self.lbl_heave_speed.setText(f"{heave_spd:+.2f} m/s")
        self.lbl_turn_rate.setText(f"{yaw_spd:+.1f} °/s ({math.radians(yaw_spd):+.2f} rad/s)")

        # Thruster Bars
        self.bar_surge.setValue(int(telemetry["thrust_surge"] * 100))
        self.bar_sway.setValue(int(telemetry["thrust_sway"] * 100))
        self.bar_heave.setValue(int(telemetry["thrust_heave"] * 100))
        self.bar_yaw.setValue(int(telemetry["thrust_yaw"] * 100))

        # Water Current Status
        c_spd = telemetry.get("current_speed", 0.0)
        c_dir = telemetry.get("current_direction", 0.0)
        c_vert = telemetry.get("current_vertical", 0.0)
        if c_spd > 0.0 or c_vert > 0.0:
            vert_str = f" + {c_vert:.2f}m/s suction" if c_vert > 0.0 else ""
            self.lbl_cur_status.setText(f"🌊 DRIFT: {c_spd:.2f} m/s @ {c_dir:.0f}°{vert_str}")
            self.lbl_cur_status.setStyleSheet("color: #facc15; font-weight: bold; font-size: 12px;")
        else:
            self.lbl_cur_status.setText("🌊 Current: CALM (No Drift)")
            self.lbl_cur_status.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 12px;")

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right,
                           Qt.Key_W, Qt.Key_S, Qt.Key_A, Qt.Key_D):
            win = self.window()
            if win:
                win.keyPressEvent(event)
                return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right,
                           Qt.Key_W, Qt.Key_S, Qt.Key_A, Qt.Key_D):
            win = self.window()
            if win:
                win.keyReleaseEvent(event)
                return
        super().keyReleaseEvent(event)

