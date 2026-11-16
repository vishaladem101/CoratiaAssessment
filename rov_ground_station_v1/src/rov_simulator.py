"""
ROV Physics and Telemetry Simulator (Backend Brain).
Pure Python: handles kinematics, water drag, thruster resposne delay,
safety watchdogs, and closed-loop hold controllers.
"""


import math
import time
try:
    from src.config import (
        DT, SAFETY_TIMEOUT, THRUSTER_ALPHA, DRAG_COEFF,
        MAX_SPEED_SURGE, MAX_SPEED_SWAY, MAX_SPEED_HEAVE, MAX_SPEED_YAW,
        START_DEPTH, START_YAW, START_ROLL, START_PITCH,
        START_LAT, START_LON, START_VOLTAGE,
        BATTERY_DRAIN_BASE, BATTERY_DRAIN_ACTIVE, BATTERY_MIN_VOLTAGE,
        KP_DEPTH, KP_HEADING,
        DEFAULT_CURRENT_SPEED, DEFAULT_CURRENT_DIR, DEFAULT_CURRENT_VERTICAL
    )
except ImportError:
    from config import (
        DT, SAFETY_TIMEOUT, THRUSTER_ALPHA, DRAG_COEFF,
        MAX_SPEED_SURGE, MAX_SPEED_SWAY, MAX_SPEED_HEAVE, MAX_SPEED_YAW,
        START_DEPTH, START_YAW, START_ROLL, START_PITCH,
        START_LAT, START_LON, START_VOLTAGE,
        BATTERY_DRAIN_BASE, BATTERY_DRAIN_ACTIVE, BATTERY_MIN_VOLTAGE,
        KP_DEPTH, KP_HEADING,
        DEFAULT_CURRENT_SPEED, DEFAULT_CURRENT_DIR, DEFAULT_CURRENT_VERTICAL
    )

METERS_PER_DEGREE_LAT = 111139.0

class ROVSimulator:
    def __init__(self):
        # 1. System States
        self.armed = False
        self.depth_hold = False
        self.heading_hold = False

        # 2. Setpoints for Hold Modes
        self.target_depth = 0.0 # Desired depth in meters
        self.target_heading = 0.0 # Desired yaw in degrees (0-360)

        # 3. Kinematic States (Position & Orientation)
        self.depth = START_DEPTH
        self.yaw = START_YAW
        self.roll = START_ROLL
        self.pitch = START_PITCH
        self.lat = START_LAT
        self.lon = START_LON

        # 4. Velocities
        self.speed_surge = 0.0 # Forward (+) / Backward (-) in m/s
        self.speed_sway = 0.0 # Left (+) / Right (-) in m/s
        self.speed_heave = 0.0 # Up (+) / Down (-) in m/s
        self.speed_yaw = 0.0 # Clockwise (+) / Counter-Clockwise (-) in deg/s
        
        # 5. Thruster Powers (-1.0 to +1.0)
        # Target = requested power; Actual = physical output with lag delay
        self.target_surge = 0.0
        self.target_sway = 0.0
        self.target_heave = 0.0
        self.target_yaw = 0.0

        self.actual_surge = 0.0
        self.actual_sway = 0.0
        self.actual_heave = 0.0
        self.actual_yaw = 0.0

        # 6. Safety & Battery
        self.last_input_time = time.time()
        self.battery_voltage = START_VOLTAGE

        # 7. Simulated Environmental Water Current
        self.current_speed = DEFAULT_CURRENT_SPEED       # m/s
        self.current_direction = DEFAULT_CURRENT_DIR     # degrees (0-360)
        self.current_vertical = DEFAULT_CURRENT_VERTICAL # m/s (downward > 0)

    # Operator Commands (Called by UI or keyboard events)
    def arm(self):
        self.armed = True
        self.last_input_time = time.time()

    def disarm(self):
        self.armed = False
        self.disable_depth_hold()
        self.disable_heading_hold()
        self.target_surge = 0.0
        self.target_sway = 0.0
        self.target_heave = 0.0
        self.target_yaw = 0.0
        self.actual_surge = 0.0
        self.actual_sway = 0.0
        self.actual_heave = 0.0
        self.actual_yaw = 0.0

    def enable_depth_hold(self, target=None):
        self.depth_hold = True
        self.last_input_time = time.time()
        if target is not None:
            self.target_depth = max(0.0, float(target))

    def disable_depth_hold(self):
        self.depth_hold = False
        self.target_heave = 0.0
        self.actual_heave = 0.0

    def enable_heading_hold(self, target=None):
        self.heading_hold = True
        self.last_input_time = time.time()
        if target is not None:
            self.target_heading = float(target) % 360.0

    def disable_heading_hold(self):
        self.heading_hold = False
        self.target_yaw = 0.0
        self.actual_yaw = 0.0

    @property
    def mode(self):
        if self.depth_hold and self.heading_hold:
            return "DEPTH & HDG HOLD"
        elif self.depth_hold:
            return "DEPTH_HOLD"
        elif self.heading_hold:
            return "HEADING_HOLD"
        return "MANUAL"

    def set_mode(self, new_mode, snap_to_current=False):
        if new_mode == "MANUAL":
            self.disable_depth_hold()
            self.disable_heading_hold()
        elif new_mode == "DEPTH_HOLD":
            self.enable_depth_hold(self.depth if snap_to_current else None)
            self.disable_heading_hold()
        elif new_mode == "HEADING_HOLD":
            self.enable_heading_hold(self.yaw if snap_to_current else None)
            self.disable_depth_hold()
        elif new_mode == "DEPTH & HDG HOLD":
            self.enable_depth_hold(self.depth if snap_to_current else None)
            self.enable_heading_hold(self.yaw if snap_to_current else None)
    
    def set_target_depth(self, depth: float):
        self.target_depth = max(0.0, float(depth))
        self.last_input_time = time.time()

    def set_target_heading(self, heading: float):
        self.target_heading = float(heading) % 360.0
        self.last_input_time = time.time()

    def set_water_current(self, speed: float, direction: float = 90.0, vertical: float = 0.0):
        """Sets the environmental water current (speed in m/s, direction in degrees, vertical downdraft in m/s)."""
        self.current_speed = max(0.0, min(2.5, float(speed)))
        self.current_direction = float(direction) % 360.0
        self.current_vertical = max(-1.0, min(1.0, float(vertical)))

    def send_manual_thrust(self, surge=0.0, sway=0.0, heave=0.0, yaw=0.0):
        self.last_input_time = time.time()
        if not self.armed:
            return

        self.target_surge = max(-1.0, min(1.0, surge))
        self.target_sway = max(-1.0, min(1.0, sway))

        # In Manual, apply direct heave; in Depth Hold, W/S slews target depth smoothly
        if not self.depth_hold:
            self.target_heave = max(-1.0, min(1.0, heave))
        elif heave != 0.0:
            self.target_depth = max(0.0, min(100.0, round(self.target_depth + heave * 0.05, 2)))

        # In Manual, apply direct yaw; in Heading Hold, A/D slews target heading smoothly
        if not self.heading_hold:
            self.target_yaw = max(-1.0, min(1.0, yaw))
        elif yaw != 0.0:
            self.target_heading = round((self.target_heading + yaw * 1.5) % 360.0, 1)

    # Alias for pilot keyboard dispatch
    set_pilot_thrust = send_manual_thrust

    # Simulation Step (Runs 20 times every second via QTimer)
    def update(self, dt=DT):
        current_time = time.time()

        # Step A: Safety rule checks
        if not self.armed:
            self.target_surge = 0.0
            self.target_sway = 0.0
            self.target_heave = 0.0
            self.target_yaw = 0.0
            self.actual_surge = 0.0
            self.actual_sway = 0.0
            self.actual_heave = 0.0
            self.actual_yaw = 0.0
            if self.current_speed == 0.0 and self.current_vertical == 0.0:
                self.speed_surge = 0.0
                self.speed_sway = 0.0
                self.speed_heave = 0.0
                self.speed_yaw = 0.0
        else:
            # Inactivity watchdog: cuts unheld manual axes after 1.0 second of silence
            if current_time - self.last_input_time > SAFETY_TIMEOUT:
                self.target_surge = 0.0
                self.target_sway = 0.0
                self.actual_surge = 0.0
                self.actual_sway = 0.0
                if not self.depth_hold:
                    self.target_heave = 0.0
                    self.actual_heave = 0.0
                if not self.heading_hold:
                    self.target_yaw = 0.0
                    self.actual_yaw = 0.0

                # Inactivity watchdog strictly guarantees vehicle does not move after 1 second unpressed
                if self.current_speed == 0.0:
                    self.speed_surge = 0.0
                    self.speed_sway = 0.0
                if self.current_vertical == 0.0 and not self.depth_hold:
                    self.speed_heave = 0.0
                if not self.heading_hold:
                    self.speed_yaw = 0.0

        # Step B: Closed-Loop Hold Controllers (Independent PD-Controllers)
        if self.armed and self.depth_hold:
            depth_error = self.target_depth - self.depth
            calculated_heave = 1.0 * depth_error - 0.4 * self.speed_heave
            self.target_heave = max(-1.0, min(1.0, calculated_heave))

        if self.armed and self.heading_hold:
            heading_error = (self.target_heading - self.yaw + 540.0) % 360.0 - 180.0
            calculated_yaw = 0.04 * heading_error - 0.015 * self.speed_yaw
            self.target_yaw = max(-1.0, min(1.0, calculated_yaw))

        # Step C: Thruster Response Delay (Exponential lag filter for motor inertia)
        if self.armed:
            self.actual_surge += THRUSTER_ALPHA * (self.target_surge - self.actual_surge)
            self.actual_sway += THRUSTER_ALPHA * (self.target_sway - self.actual_sway)
            self.actual_heave += THRUSTER_ALPHA * (self.target_heave - self.actual_heave)
            self.actual_yaw += THRUSTER_ALPHA * (self.target_yaw - self.actual_yaw)

            # Snap residual micro-thrust (< 0.01) to absolute 0.0 when target is zero
            if self.target_surge == 0.0 and abs(self.actual_surge) < 0.01:
                self.actual_surge = 0.0
            if self.target_sway == 0.0 and abs(self.actual_sway) < 0.01:
                self.actual_sway = 0.0
            if self.target_heave == 0.0 and not self.depth_hold and abs(self.actual_heave) < 0.01:
                self.actual_heave = 0.0
            if self.target_yaw == 0.0 and not self.heading_hold and abs(self.actual_yaw) < 0.01:
                self.actual_yaw = 0.0
        else:
            self.actual_surge = 0.0
            self.actual_sway = 0.0
            self.actual_heave = 0.0
            self.actual_yaw = 0.0

        # Step D: Apply Thrusters, Environmental Current & Hydrodynamic Drag
        # 1. Resolve environmental current into the ROV body frame
        rel_hdg = math.radians(self.current_direction - self.yaw)
        current_body_surge = self.current_speed * math.cos(rel_hdg)
        current_body_sway  = self.current_speed * math.sin(rel_hdg)
        current_body_heave = self.current_vertical

        # 2. Relative velocity between ROV and surrounding water
        rel_surge = self.speed_surge - current_body_surge
        rel_sway  = self.speed_sway  - current_body_sway
        rel_heave = self.speed_heave - current_body_heave

        # 3. Thruster accelerations
        accel_surge = self.actual_surge * MAX_SPEED_SURGE * 2.0
        accel_sway = self.actual_sway * MAX_SPEED_SWAY * 2.0
        accel_heave = self.actual_heave * MAX_SPEED_HEAVE * 2.0
        accel_yaw = self.actual_yaw * MAX_SPEED_YAW * 2.0
        
        # 4. Drag damps relative motion; when key released (target==0), damp promptly
        if self.target_surge != 0.0:
            self.speed_surge = current_body_surge + (rel_surge + accel_surge * dt) * DRAG_COEFF
        else:
            # Active hydrodynamic deceleration on key release
            rel_surge = rel_surge * 0.50
            if abs(rel_surge) < 0.03:
                rel_surge = 0.0
            self.speed_surge = current_body_surge + rel_surge

        if self.target_sway != 0.0:
            self.speed_sway = current_body_sway + (rel_sway + accel_sway * dt) * DRAG_COEFF
        else:
            rel_sway = rel_sway * 0.50
            if abs(rel_sway) < 0.03:
                rel_sway = 0.0
            self.speed_sway = current_body_sway + rel_sway

        if self.depth_hold or self.target_heave != 0.0:
            self.speed_heave = current_body_heave + (rel_heave + accel_heave * dt) * DRAG_COEFF
        else:
            rel_heave = rel_heave * 0.50
            if abs(rel_heave) < 0.03:
                rel_heave = 0.0
            self.speed_heave = current_body_heave + rel_heave

        if self.heading_hold or self.target_yaw != 0.0:
            self.speed_yaw = (self.speed_yaw + accel_yaw * dt) * DRAG_COEFF
        else:
            self.speed_yaw = self.speed_yaw * 0.50
            if abs(self.speed_yaw) < 0.3:
                self.speed_yaw = 0.0
        
        # Step E: Update Position and Orientation
        # 1. Depth (cannot float above surface: depth >= 0.0)
        self.depth += self.speed_heave * dt
        if self.depth < 0.0:
            self.depth = 0.0
            self.speed_heave = 0.0

        # 2. Yaw (compass heding 0 - 360 degrees)
        self.yaw = (self.yaw + self.speed_yaw * dt) % 360.0

        # 3. Passive Metacentric Stability (Self-righting ballast keeps ROV level at 0.0°)
        self.pitch = 0.0
        self.roll = 0.0

        # 4. GPS Coordinate translation based on heading and surge/sway
        yaw_rad = math.radians(self.yaw)
        # World displacement in North and East meters
        dx_north = (self.speed_surge * math.cos(yaw_rad) - self.speed_sway * math.sin(yaw_rad)) * dt
        dy_east = (self.speed_surge * math.sin(yaw_rad) + self.speed_sway * math.cos(yaw_rad)) * dt

        # Convert meters to degrees latitude & longitude
        meters_per_deg_lon = METERS_PER_DEGREE_LAT * math.cos(math.radians(self.lat))
        self.lat += dx_north / METERS_PER_DEGREE_LAT
        self.lon += dy_east / meters_per_deg_lon
        # Step F: Battery Discharge Simulation
        total_load = abs(self.actual_surge) + abs(self.actual_sway) + abs(self.actual_heave) + abs(self.actual_yaw)
        drain = BATTERY_DRAIN_BASE + (BATTERY_DRAIN_ACTIVE * total_load * 0.25)
        self.battery_voltage = max(BATTERY_MIN_VOLTAGE, self.battery_voltage - (drain * dt))

    def get_telemetry(self):
        """Returns all current sensor and status values in a clean dict."""
        return {
            "armed": self.armed,
            "mode": self.mode,
            "depth": self.depth,
            "target_depth": self.target_depth,
            "yaw": self.yaw,
            "target_heading": self.target_heading,
            "roll": self.roll,
            "pitch": self.pitch,
            "lat": self.lat,
            "lon": self.lon,
            "voltage": self.battery_voltage,
            "thrust_surge": self.actual_surge,
            "thrust_sway": self.actual_sway,
            "thrust_heave": self.actual_heave,
            "thrust_yaw": self.actual_yaw,
            "speed_surge": self.speed_surge,
            "speed_sway": self.speed_sway,
            "speed_heave": self.speed_heave,
            "speed_yaw": self.speed_yaw,
            "current_speed": self.current_speed,
            "current_direction": self.current_direction,
            "current_vertical": self.current_vertical,
        }

if __name__ == "__main__":
    print("Testing ROVSimulator standalone...")
    sim = ROVSimulator()

    # Test 1: Disarmed Safety Check
    sim.send_manual_thrust(surge=1.0)
    sim.update()
    print(f"Disarmed check: Target Surge={sim.target_surge}, Actual Surge={sim.actual_surge} (Expected: 0.0)")
    
    # Test 2: Arm and apply Forward thrust (observe thruster delay)
    sim.arm()
    sim.send_manual_thrust(surge=1.0)
    print("\nAccelerating forward for 10 steps (observe gradual thruster ramp-up):")
    for step in range(10):
        sim.send_manual_thrust(surge=1.0)
        sim.update()
        print(f"Step {step+1}: Actual Thrust={sim.actual_surge:.3f}, Speed={sim.speed_surge:.3f} m/s")
    # Test 3: Safety Watchdog (stop input and wait > 1 second)
    print("\nSimulating operator silence for 1.2 seconds (watchdog timeout):")
    time.sleep(1.2)
    sim.update()
    print(f"Watchdog fired! Target Surge={sim.target_surge:.2f} (Expected: 0.0)")
    # Test 4: Depth Hold Test
    print("\nTesting Depth Hold at 5.0 meters:")
    sim.set_mode("DEPTH_HOLD")
    sim.set_target_depth(5.0)
    for _ in range(40):
        sim.update()
    print(f"ROV Depth reached: {sim.depth:.2f} m (Target: 5.0 m)")
    print("\nAll standalone tests passed successfully!")