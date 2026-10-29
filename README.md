# 基于深度强化学习的交互式投篮辅助机器人

本项目复用现有 AGV 底盘与 ROS 2 传感器、导航代码，计划增加 SO-101 机械臂，实现轻量玩具球的交互式取球、投掷与训练反馈。

**当前阶段：底盘代码基础 + 机器人技术方案设计。** 仓库中存在 AGV 控制、雷达、IMU、建图与导航启动配置；Agent、VLA、机械臂控制、MuJoCo 投掷环境和 PPO 策略尚未实现，也尚无整机性能验证结论。

## 技术方案

- [完整技术方案：Agent + VLA + DRL](docs/technical-plan.md)：研究范围、代码现状、硬件、数据采集、训练、接口、控制权交接、部署与验收。
- [技术总览原图](docs/assets/agent-vla-drl-technical-overview.png)：可下载放大查看。
- [原 AGV 项目交接文档](sensor_ws/项目交接文档.md)：底盘基础系统的历史操作说明，使用前需核对当前代码与硬件。
- [原 AGV 技术阅读指南](sensor_ws/AI阅读指南.md)：底层代码背景。

![Agent、VLA 与 DRL 技术总览](docs/assets/agent-vla-drl-technical-overview.png)

## 拟实施分工

| 模块 | 职责 | 状态 |
| --- | --- | --- |
| AGV / ROS 2 | 传感器、底盘通信、导航与停车 | 已有代码，实机能力需逐项复核 |
| Agent（Codex 或 DSH） | 理解训练意图、调用技能、处理任务反馈 | 计划接入 |
| VLA（优先试验 SmolVLA） | 根据图像、语言和关节状态完成选球、抓取与准备动作 | 计划采集示范并微调 |
| DRL（拟采用 PPO） | 学习摆臂与释放策略，评估泛化和 Sim-to-Real | 计划开发 |
| 本地任务执行器与 arm_control | 条件检查、动作执行、控制权仲裁、超时与急停联动 | 计划开发 |

第一阶段先建立“停车 → 人工装球 / 持球 → 预设摆臂 → 释放 → 恢复”的基础闭环；随后引入 VLA 取球与 DRL 投掷。供球托盘和语言条件选球属于新增设计，尚未实现。

## 仓库结构

```text
DRL-Main/
├── README.md
├── docs/
│   ├── technical-plan.md
│   └── assets/agent-vla-drl-technical-overview.png
└── sensor_ws/
    ├── src/agv_control/
    ├── src/imu_ros2_device/
    ├── src/ldlidar_ros2/
    └── src/sensor_bringup/
```

当前目标环境为 Ubuntu 24.04 / ROS 2 Jazzy；历史提交中存在 Humble 描述，实际部署版本需现场确认。本文不代表新模块已可安装或启动，实施顺序与验收条件见完整技术方案。
