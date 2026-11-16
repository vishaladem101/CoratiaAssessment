"""
Main ROV Telemetry Ground Station Dashboard Window.
Assembles the modular View components:
  - CustomTitleBar: Window header with custom dragging & controls.
  - TopCommandBar: 2-tier responsive flight controls & 5S battery status.
  - LeftTelemetryPanel: Speeds, thruster load bars, environmental drift, help.
  - RightVisualsPanel: 2D subsea water column, depth plot, offline satellite map.
  - Keyboard pilot control dispatch & main event loop synchronization.
"""
import os
import sys
import subprocess
from collections import deque

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QApplication, QLineEdit
)
from PySide6.QtCore import Qt, QEvent, QTimer
from PySide6.QtGui import QIcon

from src.view.resources import get_resource_path
from src.view.title_bar import CustomTitleBar
from src.view.top_bar import TopCommandBar
from src.view.left_panel import LeftTelemetryPanel
from src.view.right_panel import RightVisualsPanel


class ROVDashboard(QMainWindow):
    """Integrated ROV Mission Control Cockpit (View & Controller layer)."""
    def __init__(self, simulator):
        super().__init__()
        self.sim = simulator

        self.setWindowTitle("ROV Dam Inspection Ground Station - Coratia Assessment")
        icon_path = get_resource_path("rov_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.resize(1280, 820)
        self.setMinimumSize(940, 600)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()

        # Frameless window with custom maritime title bar and edge mouse tracking
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setMouseTracking(True)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #0b111a;
                border: 1.5px solid #0284c7;
            }
            QGroupBox {
                color: #93c5fd;
                font-weight: bold;
                font-size: 12px;
                border: 1px solid #1e293b;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 14px;
                background-color: #101826;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QLabel { color: #cbd5e1; font-size: 13px; }
            QComboBox, QDoubleSpinBox {
                background-color: #080d14;
                color: #38bdf8;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 4px 8px;
                font-weight: bold;
            }
            QPushButton {
                background-color: #1e293b;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 5px 10px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #334155;
                border-color: #38bdf8;
            }
            QProgressBar {
                background-color: #080d14;
                border: 1px solid #1e293b;
                border-radius: 3px;
                text-align: center;
                color: white;
                font-size: 11px;
                font-weight: bold;
                height: 15px;
            }
            QProgressBar::chunk { background-color: #0284c7; }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Custom Maritime Blue Title Bar
        self.title_bar = CustomTitleBar(self)
        root_layout.addWidget(self.title_bar)

        # 2. Main Content Container
        content_container = QWidget()
        content_container.setMouseTracking(True)
        self.main_layout = QVBoxLayout(content_container)
        self.main_layout.setSpacing(10)
        self.main_layout.setContentsMargins(12, 10, 12, 12)
        root_layout.addWidget(content_container)

        self.time_history = deque(maxlen=200)
        self.depth_history = deque(maxlen=200)
        self.elapsed_time = 0.0
        self.pressed_keys = set()

        # 3. Top Command Ribbon (2-Tier Responsive)
        self.top_bar = TopCommandBar(self.sim, self)
        self.main_layout.addWidget(self.top_bar)

        # 4. Disarm Banner
        self.banner_disarm = QLabel("⚠️ VEHICLE IS DISARMED — CLICK THE 'ARM' BUTTON ABOVE TO ENABLE THRUSTERS")
        self.banner_disarm.setAlignment(Qt.AlignCenter)
        self.banner_disarm.setStyleSheet("""
            background-color: #7f1d1d; color: #fecaca;
            font-weight: bold; font-size: 12px;
            padding: 4px; border-radius: 4px;
        """)
        self.main_layout.addWidget(self.banner_disarm)

        # 5. Body Layout: Left Telemetry & Right Visuals Panels
        body_layout = QHBoxLayout()
        body_layout.setSpacing(10)
        self.main_layout.addLayout(body_layout, stretch=1)

        self.left_panel = LeftTelemetryPanel(self.sim, self)
        self.left_panel.setMinimumWidth(320)
        self.left_panel.setMaximumWidth(420)
        body_layout.addWidget(self.left_panel, stretch=0)

        self.right_panel = RightVisualsPanel(self.sim, self)
        body_layout.addWidget(self.right_panel, stretch=1)

    # -------------------------------------------------------------
    # Window Edge Resizing & Native Mouse Tracking
    # -------------------------------------------------------------
    def mousePressEvent(self, event):
        self.setFocus()
        if event.button() == Qt.LeftButton and not self.isMaximized():
            edge = self._get_resize_edge(event.position().toPoint())
            if edge is not None and self.windowHandle():
                self.windowHandle().startSystemResize(edge)
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not self.isMaximized():
            edge = self._get_resize_edge(event.position().toPoint())
            self._update_cursor_for_edge(edge)
        super().mouseMoveEvent(event)

    def _get_resize_edge(self, pos):
        margin = 6
        rect = self.rect()
        left = pos.x() <= margin
        right = pos.x() >= rect.width() - margin
        top = pos.y() <= margin
        bottom = pos.y() >= rect.height() - margin

        if top and left:
            return Qt.TopEdge | Qt.LeftEdge
        if top and right:
            return Qt.TopEdge | Qt.RightEdge
        if bottom and left:
            return Qt.BottomEdge | Qt.LeftEdge
        if bottom and right:
            return Qt.BottomEdge | Qt.RightEdge
        if left:
            return Qt.LeftEdge
        if right:
            return Qt.RightEdge
        if top:
            return Qt.TopEdge
        if bottom:
            return Qt.BottomEdge
        return None

    def _update_cursor_for_edge(self, edge):
        if edge in (Qt.TopEdge | Qt.LeftEdge, Qt.BottomEdge | Qt.RightEdge):
            self.setCursor(Qt.SizeFDiagCursor)
        elif edge in (Qt.TopEdge | Qt.RightEdge, Qt.BottomEdge | Qt.LeftEdge):
            self.setCursor(Qt.SizeBDiagCursor)
        elif edge in (Qt.LeftEdge, Qt.RightEdge):
            self.setCursor(Qt.SizeHorCursor)
        elif edge in (Qt.TopEdge, Qt.BottomEdge):
            self.setCursor(Qt.SizeVerCursor)
        else:
            self.unsetCursor()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange:
            if hasattr(self, 'title_bar') and hasattr(self.title_bar, 'btn_maximize'):
                if self.isMaximized():
                    self.title_bar.btn_maximize.setText("❐")
                else:
                    self.title_bar.btn_maximize.setText("🗖")

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_dark_title_bar()
        QTimer.singleShot(150, self._apply_dark_title_bar)

    def _apply_dark_title_bar(self):
        """Forces the OS native window manager (Ubuntu GNOME, Windows 10/11) to render dark title accents."""
        if sys.platform.startswith("linux"):
            try:
                win_id = int(self.winId())
                subprocess.run(
                    ["xprop", "-id", str(win_id), "-f", "_GTK_THEME_VARIANT", "8u", "-set", "_GTK_THEME_VARIANT", "dark"],
                    capture_output=True, timeout=1
                )
            except Exception:
                pass
        elif sys.platform == "win32":
            try:
                import ctypes
                hwnd = int(self.winId())
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 20, ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int)
                )
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 19, ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int)
                )
            except Exception:
                pass

    # -------------------------------------------------------------
    # Keyboard Navigation Controls
    # -------------------------------------------------------------

    def keyPressEvent(self, event):
        if not event.isAutoRepeat():
            self.pressed_keys.add(event.key())
            self._process_keyboard_inputs()
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if not event.isAutoRepeat():
            self.pressed_keys.discard(event.key())
            self._process_keyboard_inputs()
        super().keyReleaseEvent(event)

    def changeEvent(self, event):
        """Prevent stuck keys if window loses focus."""
        if event.type() == QEvent.ActivationChange and not self.isActiveWindow():
            if self.pressed_keys:
                self.pressed_keys.clear()
                self._process_keyboard_inputs()
        super().changeEvent(event)

    def _process_keyboard_inputs(self):
        """Translates held keys into normalized pilot thrust commands (Surge, Sway, Heave, Yaw) for the 6-DOF ROV."""
        surge = 0.0
        sway = 0.0
        heave = 0.0
        yaw = 0.0

        if Qt.Key_Up in self.pressed_keys:
            surge += 1.0
        if Qt.Key_Down in self.pressed_keys:
            surge -= 1.0

        if Qt.Key_Right in self.pressed_keys:
            sway += 1.0
        if Qt.Key_Left in self.pressed_keys:
            sway -= 1.0

        if Qt.Key_W in self.pressed_keys:
            heave -= 1.0  # Surface (negative heave)
        if Qt.Key_S in self.pressed_keys:
            heave += 1.0  # Dive (positive heave)

        if Qt.Key_D in self.pressed_keys:
            yaw += 1.0    # Turn Right (Clockwise)
        if Qt.Key_A in self.pressed_keys:
            yaw -= 1.0    # Turn Left (Counter-Clockwise)

        self.sim.send_manual_thrust(surge=surge, sway=sway, heave=heave, yaw=yaw)

    # -------------------------------------------------------------
    # Main 20 Hz Synchronous Update
    # -------------------------------------------------------------
    def update_dashboard(self, telemetry):
        """Dispatches telemetry state across all modular view components."""
        self.elapsed_time += 0.05

        # Continuously refresh manual thrust while keys are held (prevents watchdog timeout during active hold)
        if self.pressed_keys:
            self._process_keyboard_inputs()

        # 1. Update Disarm Banner
        is_armed = telemetry["armed"]
        self.banner_disarm.setVisible(not is_armed)

        # 2. Update Top Command Bar
        self.top_bar.update_state(telemetry, self.sim)

        # 3. Update Left Telemetry Panel
        self.left_panel.update_telemetry(telemetry)

        # 4. Update Right Visuals Panel (2D Column, Depth Graph, Offline Satellite Map)
        self.right_panel.update_visuals(
            telemetry=telemetry,
            elapsed_time=self.elapsed_time,
            time_history=self.time_history,
            depth_history=self.depth_history,
            sim=self.sim
        )

