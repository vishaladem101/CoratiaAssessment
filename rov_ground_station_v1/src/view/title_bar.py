"""
Custom Maritime Blue Window Title Bar for frameless desktop execution.
Supports smooth OS window dragging, minimize, maximize/restore, and close.
"""
import os
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from src.view.resources import get_resource_path


class CustomTitleBar(QWidget):
    """Custom Window Title Bar Widget (Overrides System Native Title Bar)."""
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

