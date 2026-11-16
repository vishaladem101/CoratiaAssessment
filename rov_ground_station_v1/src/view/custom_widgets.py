"""
Custom interactive UI widgets:
  1. SubseaWaterColumnWidget: 2D vector water-column cross section with live ROV diving,
     surface support vessel, tether, headlights, and depth ruler.
  2. CleanSpinBox: Click-to-clear setpoint spinbox with automated suffix and blur restoration.
"""
import math
from PySide6.QtWidgets import QWidget, QDoubleSpinBox
from PySide6.QtCore import Qt, QRectF, QPointF, QEvent
from PySide6.QtGui import QFont, QColor, QPainter, QPen, QBrush, QLinearGradient


class SubseaWaterColumnWidget(QWidget):
    """2D Subsea Water Column Cross-Section rendering live depth and visual vehicle attitude."""
    def __init__(self, parent=None):
        super().__init__(parent)
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


class CleanSpinBox(QDoubleSpinBox):
    """Clean click-to-clear setpoint spinbox with automated suffix and blur restoration."""
    def __init__(self, unit='', decimals=1, parent=None):
        super().__init__(parent)
        self.unit = unit
        self.setDecimals(decimals)
        self.setSuffix(unit)
        self._is_editing = False
        self.lineEdit().installEventFilter(self)
        self.lineEdit().setContentsMargins(10, 0, 4, 0)

    @property
    def is_editing(self):
        return self._is_editing

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
        self._is_editing = False
        txt = self.lineEdit().text().strip()
        if txt:
            try:
                val = float(txt)
            except ValueError:
                val = self.value()
        else:
            val = self.value()
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

