from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    ldlidar_launch = os.path.join(get_package_share_directory("ldlidar"), "launch", "ld06.launch.py")
    rviz_config = os.path.join(
        get_package_share_directory("sensor_bringup"), "rviz", "sensor_bringup.rviz"
    )

    enable_teleop = DeclareLaunchArgument("enable_teleop", default_value="true")
    enable_rviz = DeclareLaunchArgument("enable_rviz", default_value="false")
    initial_mode = DeclareLaunchArgument("initial_mode", default_value="teleop")
    imu_port = DeclareLaunchArgument("imu_port", default_value="/dev/ttyUSB1")
    agv_host = DeclareLaunchArgument("agv_host", default_value="192.168.1.254")
    agv_port = DeclareLaunchArgument("agv_port", default_value="1024")
    command_timeout = DeclareLaunchArgument("command_timeout_sec", default_value="0.6")

    lidar = IncludeLaunchDescription(PythonLaunchDescriptionSource(ldlidar_launch))

    imu = Node(
        package="imu_ros2_device",
        executable="ybimu_driver",
        output="screen",
        parameters=[{"port_name": LaunchConfiguration("imu_port")}],
    )

    imu_tf = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="base_link_to_imu_link",
        arguments=["0", "0", "0", "0", "0", "0", "base_link", "imu_link"],
    )

    agv_bridge = Node(
        package="agv_control",
        executable="agv_bridge",
        output="screen",
        parameters=[
            {
                "host": LaunchConfiguration("agv_host"),
                "port": LaunchConfiguration("agv_port"),
                "initial_mode": LaunchConfiguration("initial_mode"),
                "command_timeout_sec": LaunchConfiguration("command_timeout_sec"),
            }
        ],
    )

    teleop = Node(
        package="agv_control",
        executable="keyboard_teleop",
        output="screen",
        condition=IfCondition(LaunchConfiguration("enable_teleop")),
    )

    imu_marker_viz = Node(
        package="sensor_bringup",
        executable="imu_marker_viz",
        output="screen",
    )

    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="sensor_bringup_rviz",
        arguments=["-d", rviz_config],
        output="screen",
        condition=IfCondition(LaunchConfiguration("enable_rviz")),
    )

    return LaunchDescription(
        [
            enable_teleop,
            enable_rviz,
            initial_mode,
            imu_port,
            agv_host,
            agv_port,
            command_timeout,
            lidar,
            imu,
            imu_tf,
            agv_bridge,
            teleop,
            imu_marker_viz,
            rviz,
        ]
    )
