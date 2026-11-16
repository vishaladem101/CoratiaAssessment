"""
ROV Ground Station View Package.
Modular UI components following the MVC (Model-View-Controller) architecture:
  - dashboard: Main ROVDashboard window assembling all components.
  - title_bar: CustomTitleBar with frameless dragging and window controls.
  - top_bar: TopCommandBar with 2-tier responsive flight controls and battery telemetry.
  - left_panel: LeftTelemetryPanel with speeds, thruster loads, current, and help.
  - right_panel: RightVisualsPanel with 2D subsea column, depth plot, and satellite map.
  - custom_widgets: SubseaWaterColumnWidget and CleanSpinBox.
  - resources: get_resource_path asset resolution utility.
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

