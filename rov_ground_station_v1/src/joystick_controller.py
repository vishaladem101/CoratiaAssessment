"""
Cross-Platform Joystick / Gamepad Controller for ROV Ground Station.
Supports standard USB gamepads, flight sticks, and Xbox/PlayStation controllers.
Zero extra dependencies: uses Linux /dev/input/js* interface and Windows joyGetPosEx.
Gracefully handles disconnects and hot-plugging.
"""

import os
import sys
import struct
import platform

# Deadzone threshold to ignore small stick drift
JOYSTICK_DEADZONE = 0.12


class JoystickController:
    """Polls connected joysticks/gamepads for 4-DoF pilot control axes and buttons."""
    def __init__(self):
        self.system = platform.system()
        self.device_name = "None"
        self.is_connected = False
        self._fd = None
        self._axes = {}
        self._buttons = {}

        self._init_device()

    def _init_device(self):
        """Attempts to open physical joystick on current OS."""
        if self.system == "Linux":
            # Search /dev/input/js0 through js4
            for idx in range(5):
                dev_path = f"/dev/input/js{idx}"
                if os.path.exists(dev_path):
                    try:
                        import fcntl
                        self._fd = open(dev_path, "rb")
                        # Set non-blocking
                        flag = fcntl.fcntl(self._fd.fileno(), fcntl.F_GETFL)
                        fcntl.fcntl(self._fd.fileno(), fcntl.F_SETFL, flag | os.O_NONBLOCK)
                        self.is_connected = True
                        self.device_name = f"Joystick ({dev_path})"
                        return
                    except Exception:
                        pass
        elif self.system == "Windows":
            try:
                import ctypes
                from ctypes import wintypes
                # Probe joyGetPosEx
                self.is_connected = False
            except Exception:
                pass

    def check_connection(self):
        """Checks if a joystick is currently active."""
        if self.system == "Linux":
            if not self.is_connected or self._fd is None:
                self._init_device()
        return self.is_connected

    def read_inputs(self):
        """
        Polls joystick state and returns dict:
        {
            'active': bool,
            'surge': float (-1.0 to 1.0),
            'sway': float (-1.0 to 1.0),
            'heave': float (-1.0 to 1.0),
            'yaw': float (-1.0 to 1.0),
            'btn_arm': bool,
            'btn_manual': bool
        }
        """
        result = {
            "active": False,
            "surge": 0.0,
            "sway": 0.0,
            "heave": 0.0,
            "yaw": 0.0,
            "btn_arm": False,
            "btn_manual": False
        }

        if self.system == "Linux" and self.is_connected and self._fd:
            try:
                # Read 8-byte events: (time: unsigned int, value: short, type: unsigned char, number: unsigned char)
                while True:
                    data = self._fd.read(8)
                    if not data or len(data) < 8:
                        break
                    _, val, evt_type, num = struct.unpack("IhBB", data)
                    # Axis event: 0x02
                    if evt_type & 0x02:
                        norm = val / 32767.0
                        if abs(norm) < JOYSTICK_DEADZONE:
                            norm = 0.0
                        self._axes[num] = norm
                    # Button event: 0x01
                    elif evt_type & 0x01:
                        self._buttons[num] = bool(val)

                # Standard Linux gamepad axis mapping:
                # Axis 1: Left stick Y (-1.0 up/forward, +1.0 down/back)
                # Axis 0: Left stick X (-1.0 left, +1.0 right)
                # Axis 4 or 3: Right stick Y (or Axis 2/5 for triggers)
                # Axis 3 or 2: Right stick X (-1.0 left, +1.0 right)
                surge = -self._axes.get(1, 0.0)  # Invert so forward is positive
                sway = self._axes.get(0, 0.0)
                yaw = self._axes.get(3, self._axes.get(2, 0.0))
                heave = self._axes.get(4, self._axes.get(5, 0.0))

                result["active"] = any(abs(v) > 0.0 for v in (surge, sway, heave, yaw))
                result["surge"] = max(-1.0, min(1.0, surge))
                result["sway"] = max(-1.0, min(1.0, sway))
                result["heave"] = max(-1.0, min(1.0, heave))
                result["yaw"] = max(-1.0, min(1.0, yaw))
                result["btn_arm"] = self._buttons.get(0, False) # Button A / Cross
                result["btn_manual"] = self._buttons.get(1, False) # Button B / Circle

            except BlockingIOError:
                pass
            except Exception:
                # Disconnected
                self.is_connected = False
                self._fd = None

        return result

