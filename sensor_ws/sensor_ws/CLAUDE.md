# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ROS 2 (Jazzy) workspace for an Autonomous Ground Vehicle (AGV) with LiDAR, IMU, SLAM, and Nav2 navigation. The system controls an AGV via **Modbus TCP**, processes sensor data, builds maps, and performs autonomous navigation.

Self-written packages: `agv_control`, `imu_ros2_device`, `sensor_bringup`.
Third-party/vendor packages: `ldlidar_ros2` (LDRobot official driver), `imu_ros2_device/vendor_ybimu/` (ybimu vendor library). Do not refactor vendor code.

## Hardware

| Device | Connection | Default |
|--------|-----------|---------|
| AGV chassis | Modbus TCP | `192.168.1.254:1024` |
| ybimu IMU | Serial | `/dev/ttyUSB1` (auto-discovers candidates) |
| LDRobot LD06 LiDAR | Serial | `/dev/wheeltec_lidar` or `/dev/ttyUSB0` |

**AGV Modbus protocol**: Write register address 4 with value 1=forward / 2=backward / 3=left / 4=right / 5=stop. The device also sends unsolicited **heartbeat frames** (lead byte `0xBB`, 34 bytes total) on the TCP connection — all Modbus response parsing must filter these out first. See `agv_bridge.py` `ModbusAgvClient` for the reference implementation.

**Odometry**: The AGV has no wheel encoders. `command_odom.py` dead-reckons pose from discrete command codes using fixed speed constants (forward 0.20 m/s, backward 0.16 m/s, turn 0.75 rad/s). This is inherently approximate.

## Build & Development Commands

```bash
# Source ROS 2 and workspace
source /opt/ros/jazzy/setup.bash
source install/setup.bash

# Build all packages
colcon build

# Build a single package
colcon build --packages-select agv_control
colcon build --packages-select ldlidar
colcon build --packages-select imu_ros2_device
colcon build --packages-select sensor_bringup

# Run tests (linting) for Python packages
colcon test --packages-select agv_control
colcon test --event-handlers console_direct+

# View test results
colcon test-result --verbose
```

## Running the System

```bash
# Sensors only (LiDAR + IMU + AGV bridge + keyboard teleop)
ros2 launch sensor_bringup sensor_bringup.launch.py

# With Rviz visualization
ros2 launch sensor_bringup sensor_bringup.launch.py enable_rviz:=true

# SLAM mapping mode
ros2 launch sensor_bringup slam_bringup.launch.py

# Autonomous navigation (requires saved map + pose graph)
ros2 launch sensor_bringup nav_bringup.launch.py

# Override hardware addresses at launch time (do not hardcode in source)
ros2 launch sensor_bringup sensor_bringup.launch.py agv_host:=192.168.1.254 agv_port:=1024 imu_port:=/dev/ttyUSB0
```

Key launch arguments: `agv_host`, `agv_port`, `imu_port`, `enable_teleop`, `initial_mode` (teleop/nav), `enable_rviz`.

## Architecture

### Package Relationships

```
sensor_bringup (orchestrator)
├── ldlidar_ros2 (C++, vendor) ────── /scan (LaserScan)
├── imu_ros2_device (Python) ─────── /imu/data_raw, /imu/mag, /euler, /baro
├── agv_control (Python)
│   ├── agv_bridge ─────────────────  Modbus TCP → AGV hardware
│   │     subscribes: /cmd_vel_teleop, /cmd_vel_nav
│   │     publishes:  /agv/current_mode, /agv/current_command
│   └── keyboard_teleop ────────────  WASD → /cmd_vel_teleop
├── command_odom ────────────────────  /agv/current_command → /odom + TF(odom→base_link)
├── imu_marker_viz ──────────────────  /imu/data_raw → Rviz CUBE marker
├── slam_toolbox ────────────────────  /scan + TF → /map + TF(map→odom)
└── nav2 ────────────────────────────  /map + /odom → /cmd_vel_nav
```

### Key Design Decisions

**Control mode switching**: `agv_bridge` subscribes to both `/cmd_vel_teleop` and `/cmd_vel_nav` simultaneously. Active mode is switched at runtime via ROS parameter or service call. This allows safe handoff between keyboard and autonomous control without restarting nodes.

**Discrete motion commands**: The AGV chassis only accepts discrete direction commands (no continuous velocity). `agv_bridge` maps Twist linear.x / angular.z thresholds to the five Modbus command codes. Fine-grained velocity control is not possible with this hardware.

**Map workflow**: (1) `slam_bringup.launch.py` to build map interactively, (2) save occupancy grid with `nav2_map_server`, (3) save SLAM pose graph via slam_toolbox service, (4) `nav_bringup.launch.py` loads both for localization + Nav2. Saved map lives in `src/sensor_bringup/maps/`.

**IMU serial auto-discovery**: `ybimu_driver.py` tries a list of port candidates in order (`/dev/myimu`, `/dev/ttyUSB1`, `/dev/ttyUSB0`, `/dev/ttyUSB2`). The `port_name` ROS parameter overrides this list.

### Configuration Files

| File | Purpose |
|------|---------|
| `src/sensor_bringup/config/nav2_params.yaml` | Nav2 stack parameters (DWB planner, max speed 0.18 m/s) |
| `src/sensor_bringup/config/slam_toolbox_mapping.yaml` | SLAM async mapping config |
| `src/sensor_bringup/config/slam_toolbox_localization.yaml` | SLAM localization config |
| `src/sensor_bringup/config/imu_filter_param.yaml` | Madgwick IMU filter params |

## Package Types

- `agv_control`, `imu_ros2_device`, `sensor_bringup` — Python (`ament_python`), linted with ament_flake8/pep257
- `ldlidar_ros2` — C++ (`ament_cmake`), linted with ament_lint_auto

## Common Pitfalls

- Always `source install/setup.bash` after any `colcon build`, or node changes won't be picked up.
- The AGV heartbeat frames will corrupt Modbus reads if not filtered — never remove the `0xBB` check in `agv_bridge.py`.
- `command_odom.py` speed constants must be re-tuned if the AGV hardware or load changes.
- `192.168.1.254` and `/dev/ttyUSB1` are environment-specific defaults. Pass them as launch arguments rather than editing source files.
