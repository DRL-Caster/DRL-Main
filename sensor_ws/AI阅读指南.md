# AI 阅读指南

本文件供 AI 编程助手（如 Claude Code）阅读，用于快速理解此代码仓库的结构、设计决策和注意事项。

---

## 项目定位

ROS 2 Jazzy 工作空间，实现工业 AGV 的自主导航。核心功能：通过 Modbus TCP 控制底盘、激光雷达 + IMU 传感器融合、slam_toolbox 建图定位、Nav2 全栈自主导航。

**自己写的包**：`agv_control`、`imu_ros2_device`、`sensor_bringup`。
**第三方/厂商包**：`ldlidar_ros2`（乐动机器人官方驱动）、`imu_ros2_device/vendor_ybimu/`（ybimu 厂商库）。不要修改第三方代码。

---

## 硬件连接

| 设备 | 连接方式 | 默认地址 |
|------|---------|---------|
| AGV 底盘 | Modbus TCP（网线） | `192.168.1.254:1024` |
| IMU（ybimu） | USB 串口 | `/dev/ttyUSB1`（自动探测候选列表） |
| 激光雷达（LDRobot LD06） | USB 串口 | `/dev/wheeltec_lidar` 或 `/dev/ttyUSB0` |

这些地址是环境默认值，通过 launch 参数 `agv_host`、`agv_port`、`imu_port` 覆盖，**不要直接改代码**。

---

## 包结构与数据流

```
sensor_bringup（总编排）
├── ldlidar_ros2（C++，厂商）────── 发布 /scan（LaserScan）
├── imu_ros2_device（Python）─────  发布 /imu/data_raw、/imu/mag、/euler、/baro
├── agv_control（Python）
│   ├── agv_bridge ──────────────── 订阅 /cmd_vel_teleop 和 /cmd_vel_nav
│   │                                发布 /agv/current_mode、/agv/current_command
│   │                                → Modbus TCP → AGV 硬件
│   └── keyboard_teleop ──────────── WASD 键盘 → /cmd_vel_teleop
├── command_odom ─────────────────── /agv/current_command → /odom + TF(odom→base_link)
├── imu_marker_viz ───────────────── /imu/data_raw → Rviz 3D 姿态可视化
├── slam_toolbox ─────────────────── /scan + TF → /map + TF(map→odom)
└── nav2 ─────────────────────────── /map + /odom → /cmd_vel_nav
```

---

## 关键设计决策

### AGV Modbus 协议与心跳包

向寄存器地址 4 写值控制运动：1=前进、2=后退、3=左转、4=右转、5=停止。

**心跳包**：AGV 设备会在 TCP 连接上主动推送心跳帧（首字节 `0xBB`，固定 34 字节）。所有 Modbus 响应解析前必须先过滤这些帧。实现见 `agv_control/agv_control/agv_bridge.py` 的 `ModbusAgvClient` 类，不要删除此逻辑。

### 里程计：无编码器，靠指令推算

AGV 硬件无轮式编码器。`command_odom.py` 监听 `/agv/current_command`，用固定速度常数做航位推算（前进 0.20 m/s、后退 0.16 m/s、转速 0.75 rad/s）。精度有限，长距离有漂移。速度常数需与实际硬件标定。

### 双话题控制模式切换

`agv_bridge` 同时订阅 `/cmd_vel_teleop`（键盘）和 `/cmd_vel_nav`（Nav2），通过 `initial_mode` 参数或运行时服务切换活跃话题，无需重启节点。

### IMU 串口自动探测

`ybimu_driver.py` 按顺序尝试 `/dev/myimu`、`/dev/ttyUSB1`、`/dev/ttyUSB0`、`/dev/ttyUSB2`。`port_name` ROS 参数可强制指定，优先级最高。

---

## 构建与运行命令

```bash
# 构建
source /opt/ros/jazzy/setup.bash
colcon build
source install/setup.bash

# 仅传感器 + 键盘遥控
ros2 launch sensor_bringup sensor_bringup.launch.py

# SLAM 建图
ros2 launch sensor_bringup slam_bringup.launch.py

# 自主导航（需已有地图）
ros2 launch sensor_bringup nav_bringup.launch.py

# 覆盖硬件地址
ros2 launch sensor_bringup sensor_bringup.launch.py agv_host:=192.168.x.x imu_port:=/dev/ttyUSB0
```

---

## 配置文件

| 文件 | 用途 |
|------|------|
| `src/sensor_bringup/config/nav2_params.yaml` | Nav2 参数（DWB 规划器，最大速度 0.18 m/s） |
| `src/sensor_bringup/config/slam_toolbox_mapping.yaml` | SLAM 建图参数（分辨率 0.05 m/格） |
| `src/sensor_bringup/config/slam_toolbox_localization.yaml` | SLAM 定位参数 |
| `src/sensor_bringup/config/imu_filter_param.yaml` | Madgwick IMU 滤波参数 |
| `src/sensor_bringup/maps/` | 已保存的场地地图（pgm + yaml + 位姿图） |

---

## 常见陷阱

- `colcon build` 后必须重新 `source install/setup.bash`，否则修改不生效。
- 不要删除 `agv_bridge.py` 中的 `0xBB` 心跳包过滤逻辑，否则 Modbus 通信必崩。
- `command_odom.py` 的速度常数与具体硬件绑定，换车或换载荷需重新标定。
- IP 地址和串口路径只通过 launch 参数改，不要硬编码进源文件。
