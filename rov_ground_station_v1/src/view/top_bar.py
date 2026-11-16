"""
Top Command Bar: Responsive 2-tier master action ribbon for safety, flight modes,
5S battery telemetry, and autopilot target hold controls.
"""
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QListView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from src.view.resources import get_resource_path
from src.view.custom_widgets import CleanSpinBox

try:
    from src.config import BATTERY_MAX_VOLTAGE, BATTERY_MIN_VOLTAGE
except ImportError:
    try:
        from config import BATTERY_MAX_VOLTAGE, BATTERY_MIN_VOLTAGE
    except ImportError:
        BATTERY_MAX_VOLTAGE = 21.0
        BATTERY_MIN_VOLTAGE = 15.0


class TopCommandBar(QFrame):
    """2-Tier responsive command ribbon preventing button clipping on narrow/half-screen displays."""
    def __init__(self, simulator, parent=None):
        super().__init__(parent)
        self.sim = simulator
        self.setObjectName("TopCommandBar")
        self.setStyleSheet("""
            QFrame#TopCommandBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #152238, stop:1 #0c1524);
                border: 1px solid #1e3b60;
                border-radius: 6px;
            }
            QLabel {
                color: #e2e8f0;
                font-weight: bold;
                font-size: 13px;
            }
        """)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(12, 8, 12, 8)
        outer_layout.setSpacing(8)

        # ---------------------------------------------------------
        # Tier 1: Arm Safety Toggle, Flight Mode & Battery Telemetry
        # ---------------------------------------------------------
        row1 = QHBoxLayout()
        row1.setSpacing(10)

        # 1. Arm Safety Toggle
        self.btn_arm = QPushButton("DISARMED")
        self.btn_arm.setCheckable(True)
        self.btn_arm.setFocusPolicy(Qt.NoFocus)
        self.btn_arm.setStyleSheet("""
            QPushButton {
                background-color: #dc2626; color: white;
                font-weight: bold; font-size: 13px;
                padding: 6px 16px; border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #ef4444;
            }
        """)
        self.btn_arm.clicked.connect(self._on_arm_toggle)
        row1.addWidget(self.btn_arm)

        # 2. Mode Dropdown & Quick Manual Resume
        row1.addWidget(QLabel("Mode:"))
        self.combo_mode = QComboBox()
        self.combo_mode.setView(QListView())
        self.combo_mode.setMaxVisibleItems(8)
        self.combo_mode.setFocusPolicy(Qt.NoFocus)
        self.combo_mode.addItems(["MANUAL", "DEPTH_HOLD", "HEADING_HOLD", "DEPTH & HDG HOLD"])
        arrow_path = get_resource_path("down_arrow.svg").replace("\\", "/")
        self.combo_mode.setStyleSheet(f"""
            QComboBox {{
                combobox-popup: 0;
                background-color: #0b1320;
                color: #38bdf8;
                border: 1.5px solid #2563eb;
                border-radius: 5px;
                padding: 5px 26px 5px 12px;
                font-weight: bold;
                font-size: 13px;
                min-width: 130px;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
                border: none;
            }}
            QComboBox::down-arrow {{
                image: url("{arrow_path}");
                width: 10px;
                height: 6px;
                margin-right: 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #0b1320;
                color: #e2e8f0;
                selection-background-color: #0284c7;
                selection-color: white;
                border: 1.5px solid #0284c7;
                border-radius: 4px;
                font-size: 13px;
                padding: 4px;
                outline: none;
            }}
        """)
        self.combo_mode.currentTextChanged.connect(self._on_mode_change)
        row1.addWidget(self.combo_mode)

        self.btn_manual = QPushButton("🕹️ MANUAL")
        self.btn_manual.setFocusPolicy(Qt.NoFocus)
        self.btn_manual.setToolTip("Release hold modes and take back manual keyboard control")
        self.btn_manual.setStyleSheet("font-size: 13px; padding: 5px 12px; font-weight: bold;")
        self.btn_manual.clicked.connect(self._on_manual_clicked)
        row1.addWidget(self.btn_manual)

        row1.addStretch()

        # 3. 5S Li-ion Battery Telemetry Readout
        self.lbl_battery = QLabel("🔋 21.00 V (100%)")
        self.lbl_battery.setFont(QFont("Monospace", 14, QFont.Bold))
        self.lbl_battery.setStyleSheet("color: #4ade80; font-size: 14px; padding: 4px 10px; background-color: #080d14; border: 1px solid #1e3a5f; border-radius: 5px; font-weight: bold;")
        self.lbl_battery.setToolTip("5S Li-ion Battery (21.0V Full, 18.5V Nominal, 15.0V Cutoff)")
        row1.addWidget(self.lbl_battery)

        outer_layout.addLayout(row1)

        # ---------------------------------------------------------
        # Tier 2: Autopilot Target Guidance & Action Buttons
        # ---------------------------------------------------------
        row2 = QHBoxLayout()
        row2.setSpacing(10)

        # Target Depth Spinbox + Lifecycle Button
        row2.addWidget(QLabel("Target Depth:"))
        self.spin_depth = CleanSpinBox(unit=" m", decimals=1)
        self.spin_depth.setRange(0.0, 100.0)
        self.spin_depth.setValue(0.0)
        self.spin_depth.setStyleSheet("""
            QDoubleSpinBox {
                font-size: 13px;
                font-weight: bold;
                padding: 4px 8px;
                min-width: 80px;
                background-color: #080d14;
                color: #38bdf8;
                border: 1px solid #334155;
                border-radius: 5px;
            }
            QDoubleSpinBox:focus {
                border-color: #38bdf8;
            }
        """)
        row2.addWidget(self.spin_depth)
        self.spin_depth.valueChanged.connect(self._on_depth_spin_changed)
        self.spin_depth.editingFinished.connect(self._release_focus_to_window)

        self.btn_depth_hold = QPushButton("⚓ ENGAGE DEPTH HOLD")
        self.btn_depth_hold.setFocusPolicy(Qt.NoFocus)
        self.btn_depth_hold.setStyleSheet("background-color: #0369a1; color: white; font-size: 13px; padding: 5px 12px; font-weight: bold;")
        self.btn_depth_hold.clicked.connect(self._on_depth_hold_button_clicked)
        row2.addWidget(self.btn_depth_hold)

        row2.addSpacing(16)

        # Target Heading Spinbox + Lifecycle Button
        row2.addWidget(QLabel("Target Heading:"))
        self.spin_heading = CleanSpinBox(unit="°", decimals=0)
        self.spin_heading.setRange(0.0, 359.0)
        self.spin_heading.setValue(0.0)
        self.spin_heading.setStyleSheet("""
            QDoubleSpinBox {
                font-size: 13px;
                font-weight: bold;
                padding: 4px 8px;
                min-width: 80px;
                background-color: #080d14;
                color: #38bdf8;
                border: 1px solid #334155;
                border-radius: 5px;
            }
            QDoubleSpinBox:focus {
                border-color: #38bdf8;
            }
        """)
        row2.addWidget(self.spin_heading)
        self.spin_heading.valueChanged.connect(self._on_heading_spin_changed)
        self.spin_heading.editingFinished.connect(self._release_focus_to_window)

        self.btn_heading_hold = QPushButton("🧭 ENGAGE HEADING HOLD")
        self.btn_heading_hold.setFocusPolicy(Qt.NoFocus)
        self.btn_heading_hold.setStyleSheet("background-color: #0369a1; color: white; font-size: 13px; padding: 5px 12px; font-weight: bold;")
        self.btn_heading_hold.clicked.connect(self._on_heading_hold_button_clicked)
        row2.addWidget(self.btn_heading_hold)

        row2.addStretch()

        outer_layout.addLayout(row2)

    # -------------------------------------------------------------
    # Callbacks
    # -------------------------------------------------------------
    def _on_arm_toggle(self, checked):
        win = self.window()
        if win:
            win.setFocus()
        if checked:
            self.sim.arm()
            self.btn_arm.setText("ARMED")
            self.btn_arm.setStyleSheet("""
                QPushButton {
                    background-color: #16a34a; color: white;
                    font-weight: bold; font-size: 13px;
                    padding: 6px 16px; border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #22c55e;
                }
            """)
        else:
            self.sim.disarm()
            self.btn_arm.setText("DISARMED")
            self.btn_arm.setStyleSheet("""
                QPushButton {
                    background-color: #dc2626; color: white;
                    font-weight: bold; font-size: 13px;
                    padding: 6px 16px; border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #ef4444;
                }
            """)

    def _release_focus_to_window(self):
        """Returns keyboard focus to the main window after finishing spinbox input."""
        win = self.window()
        if win:
            win.setFocus()

    def _on_depth_spin_changed(self, val):
        self.sim.set_target_depth(val)

    def _on_heading_spin_changed(self, val):
        self.sim.set_target_heading(val)

    def _on_mode_change(self, mode):
        self._release_focus_to_window()
        if mode == "DEPTH_HOLD":
            # Switched via dropdown: lock onto CURRENT depth where the vehicle is right now
            current_d = round(self.sim.depth, 1)
            self.sim.set_target_depth(current_d)
            self.sim.set_mode("DEPTH_HOLD", snap_to_current=True)
            self.spin_depth.blockSignals(True)
            self.spin_depth.setValue(current_d)
            self.spin_depth.blockSignals(False)
        elif mode == "HEADING_HOLD":
            # Switched via dropdown: lock onto CURRENT heading where vehicle is facing right now
            current_hdg = round(self.sim.yaw, 0)
            self.sim.set_target_heading(current_hdg)
            self.sim.set_mode("HEADING_HOLD", snap_to_current=True)
            self.spin_heading.blockSignals(True)
            self.spin_heading.setValue(current_hdg)
            self.spin_heading.blockSignals(False)
        elif mode == "DEPTH & HDG HOLD":
            current_d = round(self.sim.depth, 1)
            current_hdg = round(self.sim.yaw, 0)
            self.sim.set_target_depth(current_d)
            self.sim.set_target_heading(current_hdg)
            self.sim.set_mode("DEPTH & HDG HOLD", snap_to_current=True)
            self.spin_depth.blockSignals(True)
            self.spin_depth.setValue(current_d)
            self.spin_depth.blockSignals(False)
            self.spin_heading.blockSignals(True)
            self.spin_heading.setValue(current_hdg)
            self.spin_heading.blockSignals(False)
        else:
            self.sim.set_mode("MANUAL")

    def _on_manual_clicked(self):
        win = self.window()
        if win:
            win.setFocus()
        self.combo_mode.blockSignals(True)
        self.combo_mode.setCurrentText("MANUAL")
        self.combo_mode.blockSignals(False)
        self.sim.set_mode("MANUAL")

    def _on_depth_hold_button_clicked(self):
        self.spin_depth.finish_edit()
        win = self.window()
        if win:
            win.setFocus()
        if self.sim.depth_hold:
            self.sim.disable_depth_hold()
        else:
            target = self.spin_depth.value()
            self.sim.enable_depth_hold(target)

    def _on_heading_hold_button_clicked(self):
        self.spin_heading.finish_edit()
        win = self.window()
        if win:
            win.setFocus()
        if self.sim.heading_hold:
            self.sim.disable_heading_hold()
        else:
            target = self.spin_heading.value()
            self.sim.enable_heading_hold(target)

    def update_state(self, telemetry, sim):
        """Synchronizes top bar controls with latest telemetry state."""
        # 0. Sync spinbox values when user is not actively typing
        if not self.spin_depth.is_editing and not self.spin_depth.hasFocus():
            if abs(self.spin_depth.value() - sim.target_depth) > 0.05:
                self.spin_depth.blockSignals(True)
                self.spin_depth.setValue(round(sim.target_depth, 1))
                self.spin_depth.blockSignals(False)

        if not self.spin_heading.is_editing and not self.spin_heading.hasFocus():
            if abs(self.spin_heading.value() - sim.target_heading) > 0.5:
                self.spin_heading.blockSignals(True)
                self.spin_heading.setValue(round(sim.target_heading, 0))
                self.spin_heading.blockSignals(False)

        # 1. Arm button state
        is_armed = telemetry["armed"]
        if self.btn_arm.isChecked() != is_armed:
            self.btn_arm.blockSignals(True)
            self.btn_arm.setChecked(is_armed)
            self.btn_arm.setText("ARMED" if is_armed else "DISARMED")
            self.btn_arm.setStyleSheet(
                "background-color: #16a34a; color: white; font-weight: bold; font-size: 13px; padding: 6px 16px; border-radius: 5px;"
                if is_armed else
                "background-color: #dc2626; color: white; font-weight: bold; font-size: 13px; padding: 6px 16px; border-radius: 5px;"
            )
            self.btn_arm.blockSignals(False)

        # 2. Mode Dropdown Sync
        mode_str = telemetry["mode"]
        if self.combo_mode.currentText() != mode_str:
            self.combo_mode.blockSignals(True)
            self.combo_mode.setCurrentText(mode_str)
            self.combo_mode.blockSignals(False)

        if mode_str == "MANUAL":
            self.btn_manual.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold; font-size: 13px; padding: 5px 12px; border: 1.5px solid #38bdf8; border-radius: 5px;")
        else:
            self.btn_manual.setStyleSheet("background-color: #1e293b; color: #94a3b8; font-size: 13px; padding: 5px 12px; border: 1px solid #334155; border-radius: 5px;")

        # 3. Dynamic Lifecycle Buttons (Compact responsive text)
        depth = telemetry["depth"]
        yaw = telemetry["yaw"]

        # Depth Hold Button
        if sim.depth_hold:
            depth_err = abs(depth - sim.target_depth)
            if depth_err > 0.15:
                self.btn_depth_hold.setText(f"⏳ DIVING {sim.target_depth:.1f}m (CANCEL)")
                self.btn_depth_hold.setStyleSheet("background-color: #d97706; color: white; font-weight: bold; font-size: 13px; padding: 5px 12px;")
            else:
                self.btn_depth_hold.setText(f"🟢 HOLDING {sim.target_depth:.1f}m (RELEASE)")
                self.btn_depth_hold.setStyleSheet("background-color: #16a34a; color: white; font-weight: bold; font-size: 13px; padding: 5px 12px;")
        else:
            self.btn_depth_hold.setText("⚓ ENGAGE DEPTH HOLD")
            self.btn_depth_hold.setStyleSheet("background-color: #0369a1; color: white; font-size: 13px; padding: 5px 12px;")

        # Heading Hold Button
        if sim.heading_hold:
            hdg_err = abs((sim.target_heading - yaw + 540.0) % 360.0 - 180.0)
            if hdg_err > 2.5:
                self.btn_heading_hold.setText(f"⏳ TURNING {sim.target_heading:.0f}° (CANCEL)")
                self.btn_heading_hold.setStyleSheet("background-color: #d97706; color: white; font-weight: bold; font-size: 13px; padding: 5px 12px;")
            else:
                self.btn_heading_hold.setText(f"🟢 HOLDING {sim.target_heading:.0f}° (RELEASE)")
                self.btn_heading_hold.setStyleSheet("background-color: #16a34a; color: white; font-weight: bold; font-size: 13px; padding: 5px 12px;")
        else:
            self.btn_heading_hold.setText("🧭 ENGAGE HEADING HOLD")
            self.btn_heading_hold.setStyleSheet("background-color: #0369a1; color: white; font-size: 13px; padding: 5px 12px;")

        # 4. Battery Readout (5S Li-ion / NMC: 21.0V Full, 18.5V Nominal, 15.0V Cutoff)
        v = telemetry["voltage"]
        pct = max(0, min(100, int((v - BATTERY_MIN_VOLTAGE) / (BATTERY_MAX_VOLTAGE - BATTERY_MIN_VOLTAGE) * 100)))
        if pct > 40:
            color = "#4ade80"  # Green
        elif pct > 20:
            color = "#facc15"  # Yellow
        else:
            color = "#ef4444"  # Red
        self.lbl_battery.setText(f"🔋 {v:.2f} V ({pct}%)")
        self.lbl_battery.setStyleSheet(f"color: {color}; font-size: 14px; padding: 4px 10px; background-color: #080d14; border: 1px solid #1e3a5f; border-radius: 5px; font-weight: bold;")

