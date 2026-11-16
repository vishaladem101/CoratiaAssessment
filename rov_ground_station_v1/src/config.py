"""
Configuration constants for the ROV Ground Station.
Clean, minimal, and easy to explain.
"""

# Simulation Timing
DT = 0.05             # 50 ms tick interval (20 Hz)
SAFETY_TIMEOUT = 1.0  # Seconds of silence before auto-cutting thrust in Manual mode

# Dynamics & Physics
THRUSTER_ALPHA = 0.25 # Motor lag factor (0.0 to 1.0; 0.25 gives ~0.5s smooth ramp-up)
DRAG_COEFF = 0.88     # Damping factor per step (water resistance)
MAX_SPEED_SURGE = 1.8 # Forward/backward max speed in m/s
MAX_SPEED_SWAY = 1.2  # Lateral strafe max speed in m/s
MAX_SPEED_HEAVE = 1.4 # Vertical dive/surface max speed in m/s
MAX_SPEED_YAW = 40.0  # Turn rate in deg/s

# Initial State - Nagarjuna Sagar Dam Reservoir (Underwater Dam Inspection)
START_LAT = 16.579554   # Reservoir water surface
START_LON = 79.312759
START_DEPTH = 0.0       # 0.0 m = floating on the surface
START_YAW = 0.0         # 0.0° = North
START_ROLL = 0.0
START_PITCH = 0.0
# Real-World Subsea Robotics Battery: 5S Li-ion / NMC Pack (18.5V Nominal, 21.0V Full, 15.0V Cutoff)
# - Thrusters (e.g., T200 brushless) run at 12-24V (sweet spot 18.5-20V for max thrust & lower I^2*R loss)
# - MCU (Raspberry Pi/STM32) & sensors run on 5V/3.3V via onboard step-down buck converters
BATTERY_CELLS = 5
BATTERY_MAX_VOLTAGE = 21.0     # 4.2V / cell (100% Fully Charged)
BATTERY_NOMINAL_VOLTAGE = 18.5 # 3.7V / cell (Working nominal voltage ~18.5-19.0V)
BATTERY_MIN_VOLTAGE = 15.0     # 3.0V / cell (Safe discharge cutoff limit)
START_VOLTAGE = 21.0           # Pre-dive initial state: 100% fully charged battery
BATTERY_DRAIN_BASE = 0.0003    # Continuous electronics draw (MCU, camera, IMU, depth sensor)
BATTERY_DRAIN_ACTIVE = 0.0030  # Active load when thrusters fire under pilot or autopilot command

# Closed-Loop P-Gains
KP_DEPTH = 0.6    # Corrective vertical thrust per meter of depth error
KP_HEADING = 0.02 # Corrective yaw thrust per degree of heading error

# Simulated Water Current (Hydrodynamic Environmental Drift)
DEFAULT_CURRENT_SPEED = 0.0     # m/s (0.0 = Calm/Still Water)
DEFAULT_CURRENT_DIR = 90.0      # Degrees (0-360°; 90° = Flowing toward East)
DEFAULT_CURRENT_VERTICAL = 0.0  # m/s (Downward downdraft near dam intake gates)
