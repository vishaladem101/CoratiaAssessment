"""
ROV Ground Station - User Interface Dashboard.
Features:
 1. Subsea Water Column: Live 2D water view showing the ROV diving underwater.
 2. Live Depth-vs-Time Graph with target depth setpoint line.
 3. High-Resolution Satellite Map with infinite zoom scaling (never turns white).
 4. Thruster Power Bars + Live Speedometers (Surge m/s, Dive m/s, Turn °/s).
 5. Autopilot Lifecycle Buttons (Engage -> Transit -> Maintained -> Release).
 6. Dynamic 3-Stage Target Transit & Hold Controllers (Depth & Heading).
"""

import os
import sys
import math
import subprocess
from collections import deque

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QDoubleSpinBox,
    QGroupBox, QGridLayout, QFrame, QProgressBar, QCheckBox, QListView
)
from PySide6.QtCore import Qt, QUrl, QRectF, QPointF, QEvent, QTimer
from PySide6.QtGui import QFont, QColor, QPainter, QPen, QBrush, QLinearGradient, QIcon
import pyqtgraph as pg

try:
    from src.config import BATTERY_MAX_VOLTAGE, BATTERY_MIN_VOLTAGE, BATTERY_NOMINAL_VOLTAGE
except ImportError:
    try:
        from config import BATTERY_MAX_VOLTAGE, BATTERY_MIN_VOLTAGE, BATTERY_NOMINAL_VOLTAGE
    except ImportError:
        BATTERY_MAX_VOLTAGE = 21.0
        BATTERY_MIN_VOLTAGE = 15.0
        BATTERY_NOMINAL_VOLTAGE = 18.5

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEngineSettings
    WEBENGINE_AVAILABLE = True
except ImportError:
    WEBENGINE_AVAILABLE = False


def get_resource_path(relative_path):
    """Returns absolute path to resource, working in dev mode, modular directories, and PyInstaller bundles."""
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    # 1. Direct path check
    direct = os.path.join(base_path, relative_path)
    if os.path.exists(direct):
        return direct
    # 2. Check in assets/ subdirectory
    in_assets = os.path.join(base_path, "assets", relative_path)
    if os.path.exists(in_assets):
        return in_assets
    # 3. Check in parent's assets/ (if called from inside src/)
    parent_assets = os.path.join(os.path.dirname(base_path), "assets", relative_path)
    if os.path.exists(parent_assets):
        return parent_assets
    # 4. Check parent dir directly
    parent_direct = os.path.join(os.path.dirname(base_path), relative_path)
    if os.path.exists(parent_direct):
        return parent_direct
    return direct


# =================================================================
# Custom Widget: 2D Subsea Water Column Cross-Section
# =================================================================
class SubseaWaterColumnWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.depth = 0.0
        self.target_depth = 0.0
        self.mode = "MANUAL"
        self.thrust_heave = 0.0
        self.current_speed = 0.0
        self.current_vertical = 0.0
        self.setMinimumWidth(180)
        self.setMaximumWidth(220)

    def update_state(self, depth, target_depth, mode, thrust_heave, current_speed=0.0, current_vertical=0.0):
        self.depth = depth
        self.target_depth = target_depth
        self.mode = mode
        self.thrust_heave = thrust_heave
        self.current_speed = current_speed
        self.current_vertical = current_vertical
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        surface_y = 35.0
        max_depth_m = max(10.0, float(math.ceil((max(self.depth, self.target_depth) + 1.0) / 5.0) * 5.0))
        usable_h = h - surface_y - 25.0

        # Sky Background
        painter.fillRect(0, 0, w, int(surface_y), QColor("#09101d"))

        # Water Gradient
        water_grad = QLinearGradient(0, surface_y, 0, h)
        water_grad.setColorAt(0.0, QColor(14, 116, 144, 210))
        water_grad.setColorAt(0.5, QColor(3, 73, 110, 240))
        water_grad.setColorAt(1.0, QColor(2, 20, 45, 255))
        painter.fillRect(0, int(surface_y), w, int(h - surface_y), water_grad)

        # Waves Line
        painter.setPen(QPen(QColor("#38bdf8"), 2.0))
        painter.drawLine(0, int(surface_y), w, int(surface_y))

        # Depth Ruler
        painter.setPen(QPen(QColor("#94a3b8"), 1))
        painter.setFont(QFont("Monospace", 9))
        step = 2 if max_depth_m <= 10.0 else (5 if max_depth_m <= 30.0 else 10)
        for m in range(0, int(max_depth_m) + 1, step):
            y = surface_y + (m / max_depth_m) * usable_h
            painter.drawLine(6, int(y), 18, int(y))
            painter.drawText(22, int(y + 4), f"{m}m")

        # Water Current Indicator in Water Column
        if self.current_speed > 0.0 or self.current_vertical > 0.0:
            painter.setPen(QPen(QColor("#facc15"), 1))
            painter.setFont(QFont("Monospace", 8, QFont.Bold))
            drift_txt = f"🌊 {self.current_speed:.1f}m/s"
            if self.current_vertical > 0.0:
                drift_txt += " ↓"
            painter.drawText(int(w - 75), int(surface_y + 14), drift_txt)

        # Surface Support Boat
        center_x = w * 0.62
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#f8fafc")))
        boat_points = [
            QPointF(center_x - 18, surface_y),
            QPointF(center_x + 18, surface_y),
            QPointF(center_x + 12, surface_y - 10),
            QPointF(center_x - 14, surface_y - 10)
        ]
        painter.drawPolygon(boat_points)
        painter.setBrush(QBrush(QColor("#ef4444")))
        painter.drawRect(int(center_x - 5), int(surface_y - 16), 10, 6)

        # Target Depth Line
        if self.mode in ("DEPTH_HOLD", "DEPTH & HDG HOLD"):
            clamped_target = min(self.target_depth, max_depth_m)
            target_y = surface_y + (clamped_target / max_depth_m) * usable_h
            painter.setPen(QPen(QColor("#facc15"), 1.5, Qt.DashLine))
            painter.drawLine(35, int(target_y), w - 8, int(target_y))

        # ROV Y-position based on depth
        clamped_depth = min(self.depth, max_depth_m)
        rov_y = surface_y + (clamped_depth / max_depth_m) * usable_h

        # Tether Cable
        painter.setPen(QPen(QColor("#f59e0b"), 1.8, Qt.DotLine))
        painter.drawLine(int(center_x), int(surface_y), int(center_x), int(rov_y - 10))

        # Underwater ROV Robot
        rov_w, rov_h = 32.0, 18.0
        rx = center_x - (rov_w / 2.0)
        ry = rov_y - (rov_h / 2.0)

        # Light beam
        beam_grad = QLinearGradient(rx + rov_w, ry + 6, rx + rov_w + 35, ry + 20)
        beam_grad.setColorAt(0.0, QColor(56, 189, 248, 120))
        beam_grad.setColorAt(1.0, QColor(56, 189, 248, 0))
        painter.setBrush(QBrush(beam_grad))
        painter.setPen(Qt.NoPen)
        light_cone = [
            QPointF(rx + rov_w, ry + 4),
            QPointF(rx + rov_w + 40, ry - 6),
            QPointF(rx + rov_w + 40, ry + 24),
            QPointF(rx + rov_w, ry + 14)
        ]
        painter.drawPolygon(light_cone)

        # Thrusters
        painter.setBrush(QBrush(QColor("#1e293b")))
        painter.setPen(QPen(QColor("#0284c7"), 1))
        painter.drawRect(int(rx - 4), int(ry + 2), 5, int(rov_h - 4))

        # Main Chassis (Safety Yellow)
        painter.setBrush(QBrush(QColor("#fbbf24")))
        painter.setPen(QPen(QColor("#d97706"), 1.5))
        painter.drawRoundedRect(QRectF(rx, ry, rov_w, rov_h), 4, 4)

        # Camera Dome
        painter.setBrush(QBrush(QColor("#38bdf8")))
        painter.setPen(QPen(QColor("#0284c7"), 1))
        painter.drawEllipse(int(rx + rov_w - 5), int(ry + 4), 7, 10)

        # Depth Label Bubble
        painter.setPen(QPen(QColor("#ffffff"), 1))
        painter.setFont(QFont("Monospace", 9, QFont.Bold))
        painter.drawText(int(rx - 48), int(ry + 13), f"{self.depth:.1f}m")


# =================================================================
# Clean SpinBox: Auto-clears completely on click, restores unit on confirm/blur
# =================================================================
class CleanSpinBox(QDoubleSpinBox):
    def __init__(self, unit='', decimals=1, parent=None):
        super().__init__(parent)
        self.unit = unit
        self.setDecimals(decimals)
        self.setSuffix(unit)
        self._is_editing = False
        self.lineEdit().installEventFilter(self)
        self.lineEdit().setContentsMargins(10, 0, 4, 0)

    def eventFilter(self, obj, event):
        if obj == self.lineEdit():
            if event.type() in (QEvent.FocusIn, QEvent.MouseButtonPress):
                if not self._is_editing:
                    self._is_editing = True
                    self.setSuffix('')
                    self.lineEdit().clear()
        return super().eventFilter(obj, event)

    def focusOutEvent(self, event):
        self.finish_edit()
        super().focusOutEvent(event)

    def setValue(self, val):
        self._is_editing = False
        self.setSuffix(self.unit)
        super().setValue(val)

    def finish_edit(self):
        txt = self.lineEdit().text().strip()
        if txt:
            try:
                val = float(txt)
            except ValueError:
                val = self.value()
        else:
            val = 0.0
        self.setValue(val)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Escape):
            self.finish_edit()
            self.clearFocus()
            win = self.window()
            if win:
                win.setFocus()
            return
        super().keyPressEvent(event)


# =================================================================
# Custom Window Title Bar Widget (Overrides System Native Title Bar)
# Light Blue Theme matching the Manual button (#0284c7)
# =================================================================
class CustomTitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(38)
        self.setObjectName("CustomWindowTitleBar")
        self.setStyleSheet("""
            QWidget#CustomWindowTitleBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0284c7, stop:1 #0369a1);
                border-bottom: 1.5px solid #38bdf8;
            }
            QLabel#WindowTitleLabel {
                color: #ffffff;
                font-weight: bold;
                font-size: 25px;
                letter-spacing: 0.5px;
            }
            QPushButton.titleBtn {
                background-color: transparent;
                color: #ffffff;
                font-size: 15px;
                font-weight: bold;
                border: none;
                width: 48px;
                height: 38px;
            }
            QPushButton.titleBtn:hover {
                background-color: #026aa0;
                color: #ffffff;
            }
            QPushButton#BtnClose:hover {
                background-color: #dc2626;
                color: #ffffff;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 0, 0)
        layout.setSpacing(10)

        # 1. ROV Brand Icon
        icon_lbl = QLabel()
        icon_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        icon_path = get_resource_path("rov_icon.png")
        if os.path.exists(icon_path):
            pix = QIcon(icon_path).pixmap(20, 20)
            icon_lbl.setPixmap(pix)
        layout.addWidget(icon_lbl)

        # 2. Window Title Label
        self.lbl_title = QLabel("ROV Dam Inspection Ground Station - Coratia Assessment")
        self.lbl_title.setObjectName("WindowTitleLabel")
        self.lbl_title.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout.addWidget(self.lbl_title)

        layout.addStretch()

        # 3. Window Control Action Buttons
        self.btn_minimize = QPushButton("—")
        self.btn_minimize.setProperty("class", "titleBtn")
        self.btn_minimize.setFocusPolicy(Qt.NoFocus)
        self.btn_minimize.setToolTip("Minimize")
        self.btn_minimize.clicked.connect(self._on_minimize)
        layout.addWidget(self.btn_minimize)

        self.btn_maximize = QPushButton("🗖")
        self.btn_maximize.setProperty("class", "titleBtn")
        self.btn_maximize.setFocusPolicy(Qt.NoFocus)
        self.btn_maximize.setToolTip("Maximize / Restore")
        self.btn_maximize.clicked.connect(self._on_maximize_restore)
        layout.addWidget(self.btn_maximize)

        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("BtnClose")
        self.btn_close.setProperty("class", "titleBtn")
        self.btn_close.setFocusPolicy(Qt.NoFocus)
        self.btn_close.setToolTip("Close")
        self.btn_close.clicked.connect(self._on_close)
        layout.addWidget(self.btn_close)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            win = self.window()
            if win and win.windowHandle():
                win.windowHandle().startSystemMove()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._on_maximize_restore()
        super().mouseDoubleClickEvent(event)

    def _on_minimize(self):
        self.window().showMinimized()

    def _on_maximize_restore(self):
        win = self.window()
        if win.isMaximized():
            win.showNormal()
            self.btn_maximize.setText("🗖")
        else:
            win.showMaximized()
            self.btn_maximize.setText("❐")

    def _on_close(self):
        self.window().close()


# =================================================================
# Main ROV Ground Station Window
# =================================================================
class ROVDashboard(QMainWindow):
    def __init__(self, simulator):
        super().__init__()
        self.sim = simulator

        self.setWindowTitle("ROV Dam Inspection Ground Station - Coratia Assessment")
        icon_path = get_resource_path("rov_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.resize(1260, 800)
        self.setMinimumSize(1040, 680)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()

        # Frameless window with custom light-blue title bar and edge mouse tracking
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

        self._build_top_bar()
        self._build_disarm_banner()

        body_layout = QHBoxLayout()
        body_layout.setSpacing(10)
        self.main_layout.addLayout(body_layout)

        self.left_panel = self._build_left_panel()
        body_layout.addWidget(self.left_panel, stretch=1)

        self.right_panel = self._build_right_panel()
        body_layout.addWidget(self.right_panel, stretch=2)

    def mousePressEvent(self, event):
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
        left = pos.x() < margin
        right = pos.x() > rect.width() - margin
        top = pos.y() < margin
        bottom = pos.y() > rect.height() - margin

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
        """Forces the OS native window title bar (Ubuntu GNOME, Windows 10/11) to render in dark mode."""
        # 1. Linux X11 (Ubuntu GNOME / Mutter / XFCE)
        if sys.platform.startswith("linux"):
            try:
                win_id = int(self.winId())
                subprocess.run(
                    ["xprop", "-id", str(win_id), "-f", "_GTK_THEME_VARIANT", "8u", "-set", "_GTK_THEME_VARIANT", "dark"],
                    capture_output=True, timeout=1
                )
            except Exception:
                pass

        # 2. Windows 10 & 11 (DWM immersive dark mode)
        elif sys.platform == "win32":
            try:
                import ctypes
                hwnd = int(self.winId())
                # DWMWA_USE_IMMERSIVE_DARK_MODE (20 on Win11/Win10 20H1+, 19 on older Win10)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 20, ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int)
                )
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 19, ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int)
                )
            except Exception:
                pass

    # -------------------------------------------------------------
    # Top Control Bar: Mode, Staged Setpoints, and Autopilot Action Buttons
    # -------------------------------------------------------------
    def _build_top_bar(self):
        bar = QFrame()
        bar.setObjectName("TopCommandBar")
        bar.setStyleSheet("""
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
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        # 1. Arm Safety Toggle
        self.btn_arm = QPushButton("DISARMED")
        self.btn_arm.setCheckable(True)
        self.btn_arm.setFocusPolicy(Qt.NoFocus)
        self.btn_arm.setStyleSheet("""
            QPushButton {
                background-color: #dc2626; color: white;
                font-weight: bold; font-size: 14px;
                padding: 7px 18px; border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #ef4444;
            }
        """)
        self.btn_arm.clicked.connect(self._on_arm_toggle)
        layout.addWidget(self.btn_arm)

        # 2. Mode Dropdown & Quick Manual Resume
        layout.addWidget(QLabel("Mode:"))
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
                padding: 6px 28px 6px 14px;
                font-weight: bold;
                font-size: 13px;
                min-width: 150px;
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
        layout.addWidget(self.combo_mode)

        self.btn_manual = QPushButton("🕹️ MANUAL")
        self.btn_manual.setFocusPolicy(Qt.NoFocus)
        self.btn_manual.setToolTip("Release hold modes and take back manual keyboard control")
        self.btn_manual.setStyleSheet("font-size: 13px; padding: 6px 14px; font-weight: bold;")
        self.btn_manual.clicked.connect(self._on_manual_clicked)
        layout.addWidget(self.btn_manual)

        layout.addSpacing(6)

        # 3. Target Depth Spinbox + Lifecycle Button
        layout.addWidget(QLabel("Target Depth:"))
        self.spin_depth = CleanSpinBox(unit=" m", decimals=1)
        self.spin_depth.setRange(0.0, 100.0)
        self.spin_depth.setValue(0.0)
        self.spin_depth.setStyleSheet("""
            QDoubleSpinBox {
                font-size: 14px;
                font-weight: bold;
                padding-left: 10px;
                padding-right: 8px;
                padding-top: 5px;
                padding-bottom: 5px;
                min-width: 85px;
                background-color: #080d14;
                color: #38bdf8;
                border: 1px solid #334155;
                border-radius: 5px;
            }
            QDoubleSpinBox:focus {
                border-color: #38bdf8;
            }
            QLineEdit {
                padding-left: 8px;
            }
        """)
        self.spin_depth.editingFinished.connect(self.setFocus)
        layout.addWidget(self.spin_depth)

        self.btn_depth_hold = QPushButton("⚓ ENGAGE DEPTH HOLD")
        self.btn_depth_hold.setFocusPolicy(Qt.NoFocus)
        self.btn_depth_hold.setStyleSheet("background-color: #0369a1; color: white; font-size: 13px; padding: 6px 14px; font-weight: bold;")
        self.btn_depth_hold.clicked.connect(self._on_depth_hold_button_clicked)
        layout.addWidget(self.btn_depth_hold)

        layout.addSpacing(6)

        # 4. Target Heading Spinbox + Lifecycle Button
        layout.addWidget(QLabel("Target Heading:"))
        self.spin_heading = CleanSpinBox(unit="°", decimals=0)
        self.spin_heading.setRange(0.0, 359.0)
        self.spin_heading.setValue(0.0)
        self.spin_heading.setStyleSheet("""
            QDoubleSpinBox {
                font-size: 14px;
                font-weight: bold;
                padding-left: 10px;
                padding-right: 8px;
                padding-top: 5px;
                padding-bottom: 5px;
                min-width: 85px;
                background-color: #080d14;
                color: #38bdf8;
                border: 1px solid #334155;
                border-radius: 5px;
            }
            QDoubleSpinBox:focus {
                border-color: #38bdf8;
            }
            QLineEdit {
                padding-left: 8px;
            }
        """)
        self.spin_heading.editingFinished.connect(self.setFocus)
        layout.addWidget(self.spin_heading)

        self.btn_heading_hold = QPushButton("🧭 ENGAGE HEADING HOLD")
        self.btn_heading_hold.setFocusPolicy(Qt.NoFocus)
        self.btn_heading_hold.setStyleSheet("background-color: #0369a1; color: white; font-size: 13px; padding: 6px 14px; font-weight: bold;")
        self.btn_heading_hold.clicked.connect(self._on_heading_hold_button_clicked)
        layout.addWidget(self.btn_heading_hold)

        layout.addStretch()

        # 5. Battery
        self.lbl_battery = QLabel("🔋 21.00 V (100%)")
        self.lbl_battery.setFont(QFont("Monospace", 14, QFont.Bold))
        self.lbl_battery.setStyleSheet("color: #4ade80; font-size: 14px; padding: 4px 8px;")
        self.lbl_battery.setToolTip("5S Li-ion Battery (21.0V Full, 18.5V Nominal, 15.0V Cutoff)")
        layout.addWidget(self.lbl_battery)

        self.main_layout.addWidget(bar)

    def _build_disarm_banner(self):
        self.banner_disarm = QLabel("⚠️ VEHICLE IS DISARMED — CLICK THE 'ARM' BUTTON ABOVE TO ENABLE THRUSTERS")
        self.banner_disarm.setAlignment(Qt.AlignCenter)
        self.banner_disarm.setStyleSheet("""
            background-color: #7f1d1d; color: #fecaca;
            font-weight: bold; font-size: 12px;
            padding: 4px; border-radius: 4px;
        """)
        self.main_layout.addWidget(self.banner_disarm)

    # -------------------------------------------------------------
    # Left Panel: Telemetry, Speedometers, Thruster Bars & Controls
    # -------------------------------------------------------------
    def _build_left_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 1. Primary Telemetry & Physical Velocities
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

        # 2. Thruster Power Bars (Aligned with QGridLayout)
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
                    border-radius: 3px;
                }
            """)
            thruster_grid.addWidget(bar, r, 1)
            return bar

        self.bar_surge = add_bar(0, "Surge (↑/↓):")
        self.bar_sway  = add_bar(1, "Sway (←/→):")
        self.bar_heave = add_bar(2, "Heave (S/W):")
        self.bar_yaw   = add_bar(3, "Yaw (A/D):")

        layout.addWidget(grp_thrusters)

        # 3. Simulated Water Current (Hydrodynamic Environmental Drift)
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
            self.setFocus()

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

        # Set default to Calm
        apply_current(0.0, self.btn_cur_off)

        # 4. Controls Help Box
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
        return panel

    # -------------------------------------------------------------
    # Right Panel: 2D Water Column + Depth Chart + Satellite Map
    # -------------------------------------------------------------
    def _build_right_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Top Split
        top_split = QHBoxLayout()
        top_split.setSpacing(8)

        # A. 2D Subsea Water Column
        grp_subsea = QGroupBox("SUBSEA WATER COLUMN")
        subsea_layout = QVBoxLayout(grp_subsea)
        subsea_layout.setContentsMargins(6, 12, 6, 6)
        self.subsea_widget = SubseaWaterColumnWidget()
        subsea_layout.addWidget(self.subsea_widget)
        top_split.addWidget(grp_subsea)

        # B. Depth vs Time Graph
        grp_plot = QGroupBox("LIVE DEPTH PROFILE (Depth vs Time)")
        plot_layout = QVBoxLayout(grp_plot)
        plot_layout.setContentsMargins(6, 12, 6, 6)

        pg.setConfigOption('background', '#0b111a')
        pg.setConfigOption('foreground', '#94a3b8')

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.showGrid(x=True, y=True, alpha=0.25)
        self.plot_widget.setLabel('left', 'Depth', units='m')
        self.plot_widget.setLabel('bottom', 'Time Elapsed', units='s')
        self.plot_widget.getAxis('bottom').enableAutoSIPrefix(False)
        self.plot_widget.invertY(True)
        self.plot_widget.setYRange(-0.5, 6.0, padding=0.02)

        # 0m Surface Reference Line
        self.surface_line = pg.InfiniteLine(
            pos=0.0, angle=0,
            pen=pg.mkPen(color='#38bdf8', width=1.2, style=Qt.DashLine),
            label="Surface (0m)",
            labelOpts={'position': 0.15, 'color': '#38bdf8'}
        )
        self.plot_widget.addItem(self.surface_line)

        self.target_line = pg.InfiniteLine(
            pos=0.0, angle=0,
            pen=pg.mkPen(color='#facc15', width=1.5, style=Qt.DashLine),
            label="Target Depth",
            labelOpts={'position': 0.85, 'color': '#facc15'}
        )
        self.target_line.setVisible(False)
        self.plot_widget.addItem(self.target_line)

        self.curve_depth = self.plot_widget.plot(
            pen=pg.mkPen(color='#00d4ff', width=2.5),
            fillLevel=0.0,
            fillBrush=QColor(0, 212, 255, 30)
        )
        plot_layout.addWidget(self.plot_widget)
        top_split.addWidget(grp_plot, stretch=1)

        layout.addLayout(top_split, stretch=1)

        # Bottom: Satellite Dam Map (Infinite digital zoom scaling)
        grp_map = QGroupBox("SURFACE POSITION & SATELLITE TRACKING (Nagarjuna Sagar Dam)")
        map_layout = QVBoxLayout(grp_map)
        map_layout.setContentsMargins(6, 12, 6, 6)

        if WEBENGINE_AVAILABLE:
            self.web_map = QWebEngineView()
            self.web_map.page().profile().clearHttpCache()
            settings = self.web_map.settings()
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)

            html_path = get_resource_path("map_view.html")
            self.web_map.setUrl(QUrl.fromLocalFile(html_path))
            map_layout.addWidget(self.web_map)
        else:
            lbl_fallback = QLabel("Map Widget (QWebEngineView not available)")
            lbl_fallback.setAlignment(Qt.AlignCenter)
            map_layout.addWidget(lbl_fallback)

        layout.addWidget(grp_map, stretch=1)

        return panel

    # -------------------------------------------------------------
    # Callbacks & Autopilot Lifecycle Actions
    # -------------------------------------------------------------
    def mousePressEvent(self, event):
        self.setFocus()
        super().mousePressEvent(event)

    def _on_arm_toggle(self, checked):
        self.setFocus()
        if checked:
            self.sim.arm()
            self.btn_arm.setText("ARMED")
            self.btn_arm.setStyleSheet("""
                QPushButton {
                    background-color: #16a34a; color: white;
                    font-weight: bold; font-size: 13px;
                    padding: 6px 16px; border-radius: 4px;
                }
            """)
            self.banner_disarm.setVisible(False)
        else:
            self.sim.disarm()
            self.btn_arm.setText("DISARMED")
            self.btn_arm.setStyleSheet("""
                QPushButton {
                    background-color: #dc2626; color: white;
                    font-weight: bold; font-size: 13px;
                    padding: 6px 16px; border-radius: 4px;
                }
            """)
            self.banner_disarm.setVisible(True)

    def _on_mode_change(self, mode):
        self.setFocus()
        if mode == "DEPTH_HOLD":
            # Switched via dropdown: lock onto CURRENT depth where the vehicle is right now!
            current_d = round(self.sim.depth, 1)
            self.sim.set_target_depth(current_d)
            self.sim.set_mode("DEPTH_HOLD", snap_to_current=True)
            self.spin_depth.setValue(current_d)
            self.target_line.setValue(current_d)
            self.target_line.setVisible(True)
        elif mode == "HEADING_HOLD":
            # Switched via dropdown: lock onto CURRENT heading where the vehicle is facing right now!
            current_hdg = round(self.sim.yaw, 1)
            self.sim.set_target_heading(current_hdg)
            self.sim.set_mode("HEADING_HOLD", snap_to_current=True)
            self.spin_heading.setValue(current_hdg)
            self.target_line.setVisible(False)
        elif mode == "DEPTH & HDG HOLD":
            current_d = round(self.sim.depth, 1)
            current_hdg = round(self.sim.yaw, 1)
            self.sim.set_target_depth(current_d)
            self.sim.set_target_heading(current_hdg)
            self.sim.set_mode("DEPTH & HDG HOLD", snap_to_current=True)
            self.spin_depth.setValue(current_d)
            self.spin_heading.setValue(current_hdg)
            self.target_line.setValue(current_d)
            self.target_line.setVisible(True)
        else:
            self.sim.set_mode("MANUAL")
            self.target_line.setVisible(False)

    def _on_manual_clicked(self):
        """Disengages any active hold mode and returns to 100% human control"""
        self.setFocus()
        self.combo_mode.blockSignals(True)
        self.combo_mode.setCurrentText("MANUAL")
        self.combo_mode.blockSignals(False)
        self.sim.set_mode("MANUAL")
        self.target_line.setVisible(False)

    def _on_depth_hold_button_clicked(self):
        """Toggles between engaging Depth Hold and releasing to Manual"""
        self.spin_depth.finish_edit()
        self.setFocus()
        if self.sim.depth_hold:
            # Active -> Cancel and immediately zero vertical thrust
            self.sim.disable_depth_hold()
            self.target_line.setVisible(False)
        else:
            # Engage Depth Hold with currently staged depth in spinbox
            target = self.spin_depth.value()
            self.sim.enable_depth_hold(target)
            self.target_line.setValue(target)
            self.target_line.setVisible(True)

    def _on_heading_hold_button_clicked(self):
        """Toggles between engaging Heading Hold and releasing to Manual"""
        self.spin_heading.finish_edit()
        self.setFocus()
        if self.sim.heading_hold:
            # Active -> Cancel and immediately zero turning thrust
            self.sim.disable_heading_hold()
        else:
            # Engage Heading Hold with currently staged heading in spinbox
            target = self.spin_heading.value()
            self.sim.enable_heading_hold(target)

    # -------------------------------------------------------------
    # Keyboard Navigation with Continuous Holding Support
    # -------------------------------------------------------------
    def keyPressEvent(self, event):
        if not event.isAutoRepeat():
            self.pressed_keys.add(event.key())
            self._process_keyboard_driving()

    def keyReleaseEvent(self, event):
        if not event.isAutoRepeat():
            self.pressed_keys.discard(event.key())
            self._process_keyboard_driving()

    def _process_keyboard_driving(self):
        surge = 0.0  # Up / Down Arrows (Forward/Back)
        sway = 0.0   # Left / Right Arrows (Strafe)
        heave = 0.0  # S (dive) / W (surface)
        yaw = 0.0    # A / D (Turn Left/Right)

        # Up/Down Arrows: Forward / Backward (Active in all modes)
        if Qt.Key_Up in self.pressed_keys:
            surge += 1.0
        if Qt.Key_Down in self.pressed_keys:
            surge -= 1.0

        # Left/Right Arrows: Strafe Sway (Active in all modes)
        if Qt.Key_Right in self.pressed_keys:
            sway += 1.0
        if Qt.Key_Left in self.pressed_keys:
            sway -= 1.0

        # W/S: Depth Heave (S = Dive, W = Surface) - strictly locked out if depth_hold is active
        if not self.sim.depth_hold:
            if Qt.Key_S in self.pressed_keys:
                heave += 1.0
            if Qt.Key_W in self.pressed_keys:
                heave -= 1.0

        # A/D: Rotation (Yaw) - strictly locked out if heading_hold is active
        if not self.sim.heading_hold:
            if Qt.Key_D in self.pressed_keys:
                yaw += 1.0
            if Qt.Key_A in self.pressed_keys:
                yaw -= 1.0

        self.sim.send_manual_thrust(surge=surge, sway=sway, heave=heave, yaw=yaw)

    # -------------------------------------------------------------
    # 20 Hz Live Telemetry Update
    # -------------------------------------------------------------
    def update_dashboard(self, telemetry):
        # Continuous drive refresh: while keys are held down, keep feeding thrust
        if self.pressed_keys:
            self._process_keyboard_driving()

        # Sync Mode Dropdown if simulator mode changed (e.g. from pilot override)
        if self.combo_mode.currentText() != telemetry["mode"]:
            self.combo_mode.blockSignals(True)
            self.combo_mode.setCurrentText(telemetry["mode"])
            self.combo_mode.blockSignals(False)

        # 1. Update Labels & Speeds
        is_armed = telemetry["armed"]
        self.lbl_status.setText("ARMED" if is_armed else "DISARMED")
        self.lbl_status.setStyleSheet("color: #4ade80; font-size: 14px; font-weight: bold;" if is_armed else "color: #ef4444; font-size: 14px; font-weight: bold;")
        
        mode_str = telemetry["mode"]
        self.lbl_mode.setText(f" {mode_str} ")
        if mode_str == "MANUAL":
            self.lbl_mode.setStyleSheet("background-color: #0369a1; color: white; border-radius: 4px; padding: 2px 6px; font-size: 13px; font-weight: bold;")
            self.btn_manual.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold; font-size: 13px; padding: 6px 14px; border: 1.5px solid #38bdf8; border-radius: 5px;")
        elif mode_str == "DEPTH_HOLD":
            self.lbl_mode.setStyleSheet("background-color: #b45309; color: white; border-radius: 4px; padding: 2px 6px; font-size: 13px; font-weight: bold;")
            self.btn_manual.setStyleSheet("background-color: #1e293b; color: #94a3b8; font-size: 13px; padding: 6px 14px; border: 1px solid #334155; border-radius: 5px;")
        elif mode_str == "HEADING_HOLD":
            self.lbl_mode.setStyleSheet("background-color: #0e7490; color: white; border-radius: 4px; padding: 2px 6px; font-size: 13px; font-weight: bold;")
            self.btn_manual.setStyleSheet("background-color: #1e293b; color: #94a3b8; font-size: 13px; padding: 6px 14px; border: 1px solid #334155; border-radius: 5px;")
        else:  # DEPTH & HDG HOLD
            self.lbl_mode.setStyleSheet("background-color: #047857; color: white; border-radius: 4px; padding: 2px 6px; font-size: 13px; font-weight: bold;")
            self.btn_manual.setStyleSheet("background-color: #1e293b; color: #94a3b8; font-size: 13px; padding: 6px 14px; border: 1px solid #334155; border-radius: 5px;")

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

        # 2. Update Dynamic Lifecycle Buttons
        # Depth Hold Button State Machine
        if self.sim.depth_hold:
            depth_err = abs(depth - self.sim.target_depth)
            if depth_err > 0.15:
                self.btn_depth_hold.setText(f"⏳ DIVING TO {self.sim.target_depth:.1f}m (CANCEL)")
                self.btn_depth_hold.setStyleSheet("background-color: #d97706; color: white; font-weight: bold; font-size: 13px;")
            else:
                self.btn_depth_hold.setText(f"🟢 AT {self.sim.target_depth:.1f}m (RELEASE TO MANUAL)")
                self.btn_depth_hold.setStyleSheet("background-color: #16a34a; color: white; font-weight: bold; font-size: 13px;")
        else:
            self.btn_depth_hold.setText("⚓ ENGAGE DEPTH HOLD")
            self.btn_depth_hold.setStyleSheet("background-color: #0369a1; color: white; font-size: 13px;")

        # Heading Hold Button State Machine
        if self.sim.heading_hold:
            hdg_err = abs((self.sim.target_heading - yaw + 540.0) % 360.0 - 180.0)
            if hdg_err > 2.5:
                self.btn_heading_hold.setText(f"⏳ TURNING TO {self.sim.target_heading:.0f}° (CANCEL)")
                self.btn_heading_hold.setStyleSheet("background-color: #d97706; color: white; font-weight: bold; font-size: 13px;")
            else:
                self.btn_heading_hold.setText(f"🟢 AT {self.sim.target_heading:.0f}° (RELEASE TO MANUAL)")
                self.btn_heading_hold.setStyleSheet("background-color: #16a34a; color: white; font-weight: bold; font-size: 13px;")
        else:
            self.btn_heading_hold.setText("🧭 ENGAGE HEADING HOLD")
            self.btn_heading_hold.setStyleSheet("background-color: #0369a1; color: white; font-size: 13px;")

        # 3. Update Thruster Bars
        self.bar_surge.setValue(int(telemetry["thrust_surge"] * 100))
        self.bar_sway.setValue(int(telemetry["thrust_sway"] * 100))
        self.bar_heave.setValue(int(telemetry["thrust_heave"] * 100))
        self.bar_yaw.setValue(int(telemetry["thrust_yaw"] * 100))

        # 4. Battery Readout (5S Li-ion / NMC Pack: 21.0V Full, 18.5V Nominal, 15.0V Cutoff)
        v = telemetry["voltage"]
        pct = max(0, min(100, int((v - BATTERY_MIN_VOLTAGE) / (BATTERY_MAX_VOLTAGE - BATTERY_MIN_VOLTAGE) * 100)))
        if pct > 40:
            color = "#4ade80"  # Green: Healthy charge
        elif pct > 20:
            color = "#facc15"  # Yellow: Mid-mission advisory
        else:
            color = "#ef4444"  # Red: Low battery return-to-surface warning
        self.lbl_battery.setText(f"🔋 {v:.2f} V ({pct}%)")
        self.lbl_battery.setStyleSheet(f"color: {color}; font-size: 14px; padding: 4px 8px; font-weight: bold;")

        # 5. Water Current Status
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

        # 6. Update 2D Subsea Water Column Cross-Section
        self.subsea_widget.update_state(
            depth=depth,
            target_depth=self.sim.target_depth,
            mode=self.sim.mode,
            thrust_heave=telemetry["thrust_heave"],
            current_speed=c_spd,
            current_vertical=c_vert
        )

        # 7. Update Depth vs Time Graph
        self.elapsed_time += 0.05
        self.time_history.append(self.elapsed_time)
        self.depth_history.append(depth)
        self.curve_depth.setData(list(self.time_history), list(self.depth_history))

        max_y = max(6.0, depth + 1.5)
        self.plot_widget.setYRange(-0.5, max_y, padding=0.02)

        if self.sim.depth_hold:
            self.target_line.setValue(self.sim.target_depth)
            self.target_line.setVisible(True)
        else:
            self.target_line.setVisible(False)

        # 8. Update Satellite Map
        if WEBENGINE_AVAILABLE and hasattr(self, 'web_map'):
            js_call = (
                f"if (typeof updateROV === 'function') {{"
                f"updateROV({telemetry['lat']:.6f}, {telemetry['lon']:.6f}, {telemetry['yaw']:.1f}, "
                f"{c_spd:.2f}, {c_dir:.1f});"
                f"}}"
            )
            self.web_map.page().runJavaScript(js_call)
