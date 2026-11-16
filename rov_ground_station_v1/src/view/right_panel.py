"""
Right Visuals Panel:
  1. 2D Subsea Water Column Cross-Section.
  2. Live Depth Profile Chart (pyqtgraph) with surface & target reference lines.
  3. High-Resolution Offline Satellite Tracking Map (QWebEngineView + Leaflet).
"""
from collections import deque
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor
import pyqtgraph as pg

from src.view.resources import get_resource_path
from src.view.custom_widgets import SubseaWaterColumnWidget

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEngineSettings
    WEBENGINE_AVAILABLE = True

    class MapWebView(QWebEngineView):
        """WebEngine view forwarding pilot flight keys to the main window even when clicked."""
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

except ImportError:
    WEBENGINE_AVAILABLE = False
    MapWebView = None


class RightVisualsPanel(QWidget):
    """Encapsulates the 2D underwater cross-section, depth profile plot, and satellite tracking map."""
    def __init__(self, simulator, parent=None):
        super().__init__(parent)
        self.sim = simulator

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # ---------------------------------------------------------
        # Top Split: Subsea Column + Live Depth Profile
        # ---------------------------------------------------------
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
        self.plot_widget.setFocusPolicy(Qt.NoFocus)
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

        # Target Depth Reference Line
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

        # ---------------------------------------------------------
        # Bottom: Offline Satellite Dam Map (Nagarjuna Sagar Dam)
        # ---------------------------------------------------------
        grp_map = QGroupBox("SURFACE POSITION & SATELLITE TRACKING (Nagarjuna Sagar Dam)")
        map_layout = QVBoxLayout(grp_map)
        map_layout.setContentsMargins(6, 12, 6, 6)

        if WEBENGINE_AVAILABLE:
            self.web_map = MapWebView()
            self.web_map.page().profile().clearHttpCache()
            settings = self.web_map.settings()
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)

            html_path = get_resource_path("map_view.html")
            self.web_map.setUrl(QUrl.fromLocalFile(html_path))
            map_layout.addWidget(self.web_map)
        else:
            self.web_map = None
            lbl_fallback = QLabel("Map Widget (QWebEngineView not available)")
            lbl_fallback.setAlignment(Qt.AlignCenter)
            map_layout.addWidget(lbl_fallback)

        layout.addWidget(grp_map, stretch=1)

    def update_visuals(self, telemetry, elapsed_time, time_history, depth_history, sim):
        """Updates subsea cross section, depth profile history, and satellite tracking coordinates."""
        depth = telemetry["depth"]
        mode = telemetry["mode"]
        thrust_heave = telemetry["thrust_heave"]
        c_spd = telemetry.get("current_speed", 0.0)
        c_vert = telemetry.get("current_vertical", 0.0)

        # 1. 2D Subsea Cross-Section Widget
        self.subsea_widget.update_state(
            depth=depth,
            target_depth=sim.target_depth,
            mode=mode,
            thrust_heave=thrust_heave,
            current_speed=c_spd,
            current_vertical=c_vert
        )

        # 2. Depth-vs-Time Graph History
        time_history.append(elapsed_time)
        depth_history.append(depth)

        if len(time_history) > 1:
            self.curve_depth.setData(list(time_history), list(depth_history))
            t_now = time_history[-1]
            self.plot_widget.setXRange(max(0.0, t_now - 15.0), max(15.0, t_now), padding=0.01)

            max_seen = max(depth_history) if depth_history else 0.0
            highest_pt = max(6.0, max_seen + 1.0, sim.target_depth + 1.0)
            self.plot_widget.setYRange(-0.5, highest_pt, padding=0.02)

        # Target Depth Line
        if mode in ("DEPTH_HOLD", "DEPTH & HDG HOLD"):
            self.target_line.setValue(sim.target_depth)
            self.target_line.setVisible(True)
        else:
            self.target_line.setVisible(False)

        # 3. Satellite Tracking Map Position Update
        if self.web_map is not None:
            lat = telemetry.get("lat", telemetry.get("latitude", 16.579554))
            lon = telemetry.get("lon", telemetry.get("longitude", 79.312759))
            hdg = telemetry["yaw"]
            c_dir = telemetry.get("current_direction", 0.0)
            js = f"if (typeof updateROV === 'function') {{ updateROV({lat:.6f}, {lon:.6f}, {hdg:.1f}, {c_spd:.2f}, {c_dir:.1f}); }}"
            self.web_map.page().runJavaScript(js)
