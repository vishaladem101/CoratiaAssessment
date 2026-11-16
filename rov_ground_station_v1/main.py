"""
ROV Ground Station - Main Application Entrypoint.
Connects ROVSimulator with the PySide6 UI dashboard via a 20 Hz loop.
Clean, lightweight, and robust.
"""

import os
import sys
import signal

# On Linux, configure Chromium to avoid AppArmor unprivileged sandbox deadlocks
if sys.platform.startswith("linux"):
    flags = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")
    if "--no-sandbox" not in flags:
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = f"{flags} --no-sandbox --disable-dev-shm-usage".strip()

# Ensure both project root and src/ are on Python module search path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPalette, QColor

from src.config import DT
from src.rov_simulator import ROVSimulator
from src.ui_dashboard import ROVDashboard


def main():
    # Handle terminal Ctrl+C cleanly
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = QApplication(sys.argv)
    app.setApplicationName("ROV Ground Station")
    app.setStyle("Fusion")

    # Set application-wide dark palette so OS window managers and controls align
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor("#0b111a"))
    dark_palette.setColor(QPalette.WindowText, Qt.white)
    dark_palette.setColor(QPalette.Base, QColor("#080d14"))
    dark_palette.setColor(QPalette.AlternateBase, QColor("#101826"))
    dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
    dark_palette.setColor(QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.Text, Qt.white)
    dark_palette.setColor(QPalette.Button, QColor("#1e293b"))
    dark_palette.setColor(QPalette.ButtonText, Qt.white)
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Highlight, QColor("#0284c7"))
    dark_palette.setColor(QPalette.HighlightedText, Qt.white)
    app.setPalette(dark_palette)

    simulator = ROVSimulator()
    dashboard = ROVDashboard(simulator=simulator)
    dashboard.show()

    # 20 Hz Simulation Loop (fires every 50 ms)
    timer = QTimer()
    timer_interval_ms = int(DT * 1000)

    def tick():
        simulator.update(dt=DT)
        dashboard.update_dashboard(simulator.get_telemetry())

    timer.timeout.connect(tick)
    timer.start(timer_interval_ms)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
