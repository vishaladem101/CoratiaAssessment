"""
ROV Ground Station - User Interface Dashboard.
This module re-exports components from the modular `src.view` package:
  - src.view.dashboard: ROVDashboard
  - src.view.title_bar: CustomTitleBar
  - src.view.top_bar: TopCommandBar
  - src.view.left_panel: LeftTelemetryPanel
  - src.view.right_panel: RightVisualsPanel
  - src.view.custom_widgets: SubseaWaterColumnWidget, CleanSpinBox
  - src.view.resources: get_resource_path
"""

from src.view.resources import get_resource_path
from src.view.custom_widgets import SubseaWaterColumnWidget, CleanSpinBox
from src.view.title_bar import CustomTitleBar
from src.view.top_bar import TopCommandBar
from src.view.left_panel import LeftTelemetryPanel
from src.view.right_panel import RightVisualsPanel
from src.view.dashboard import ROVDashboard

__all__ = [
    "ROVDashboard",
    "CustomTitleBar",
    "TopCommandBar",
    "LeftTelemetryPanel",
    "RightVisualsPanel",
    "SubseaWaterColumnWidget",
    "CleanSpinBox",
    "get_resource_path",
]
