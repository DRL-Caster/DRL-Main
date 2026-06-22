from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    package_share = get_package_share_directory("sensor_bringup")
    sensor_bringup_launch = os.path.join(package_share, "launch", "sensor_bringup.launch.py")
    slam_params = os.path.join(package_share, "config", "slam_toolbox_mapping.yaml")
    rviz_config = os.path.join(package_share, "rviz", "nav2_navigation.rviz")

    use_sim_time = DeclareLaunchArgument("use_sim_time", default_value="false")
    enable_rviz = DeclareLaunchArgument("enable_rviz", default_value="true")
    enable_teleop = DeclareLaunchArgument("enable_teleop", default_value="true")
    imu_port = DeclareLaunchArgument("imu_port", default_value="/dev/ttyUSB1")
    agv_host = DeclareLaunchArgument("agv_host", default_value="192.168.1.254")
    agv_port = DeclareLaunchArgument("agv_port", default_value="1024")
    command_timeout = DeclareLaunchArgument("command_timeout_sec", default_value="0.6")

    sensors = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(sensor_bringup_launch),
        launch_arguments={
            "enable_teleop": LaunchConfiguration("enable_teleop"),
            "enable_rviz": "false",
            "initial_mode": "teleop",
            "imu_port": LaunchConfiguration("imu_port"),
            "agv_host": LaunchConfiguration("agv_host"),
            "agv_port": LaunchConfiguration("agv_port"),
            "command_timeout_sec": LaunchConfiguration("command_timeout_sec"),
        }.items(),
    )

    slam_toolbox = Node(
        package="slam_toolbox",
        executable="async_slam_toolbox_node",
        name="slam_toolbox",
        output="screen",
        parameters=[
            slam_params,
            {
                "use_sim_time": LaunchConfiguration("use_sim_time"),
            },
        ],
    )

    lifecycle_manager = Node(
        package="nav2_lifecycle_manager",
        executable="lifecycle_manager",
        name="lifecycle_manager_slam",
        output="screen",
        parameters=[
            {"autostart": True},
            {"node_names": ["slam_toolbox"]},
        ],
    )

    command_odom = Node(
        package="sensor_bringup",
        executable="command_odom",
        output="screen",
    )

    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="slam_rviz",
        arguments=["-d", rviz_config],
        output="screen",
        condition=IfCondition(LaunchConfiguration("enable_rviz")),
    )

    return LaunchDescription(
        [
            use_sim_time,
            enable_rviz,
            enable_teleop,
            imu_port,
            agv_host,
            agv_port,
            command_timeout,
            sensors,
            command_odom,
            slam_toolbox,
            lifecycle_manager,
            rviz,
        ]
    )
