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
    nav2_bringup_launch = os.path.join(
        get_package_share_directory("nav2_bringup"), "launch", "navigation_launch.py"
    )
    localization_params = os.path.join(package_share, "config", "slam_toolbox_localization.yaml")
    nav2_params = os.path.join(package_share, "config", "nav2_params.yaml")
    rviz_config = os.path.join(package_share, "rviz", "nav2_navigation.rviz")

    use_sim_time = DeclareLaunchArgument("use_sim_time", default_value="false")
    autostart = DeclareLaunchArgument("autostart", default_value="true")
    enable_rviz = DeclareLaunchArgument("enable_rviz", default_value="true")
    enable_teleop = DeclareLaunchArgument("enable_teleop", default_value="false")
    imu_port = DeclareLaunchArgument("imu_port", default_value="/dev/ttyUSB1")
    agv_host = DeclareLaunchArgument("agv_host", default_value="192.168.1.254")
    agv_port = DeclareLaunchArgument("agv_port", default_value="1024")
    command_timeout = DeclareLaunchArgument("command_timeout_sec", default_value="0.8")
    serialized_map = DeclareLaunchArgument("serialized_map", default_value="")
    params_file = DeclareLaunchArgument("params_file", default_value=nav2_params)

    sensors = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(sensor_bringup_launch),
        launch_arguments={
            "enable_teleop": LaunchConfiguration("enable_teleop"),
            "enable_rviz": "false",
            "initial_mode": "nav",
            "imu_port": LaunchConfiguration("imu_port"),
            "agv_host": LaunchConfiguration("agv_host"),
            "agv_port": LaunchConfiguration("agv_port"),
            "command_timeout_sec": LaunchConfiguration("command_timeout_sec"),
        }.items(),
    )

    slam_localization = Node(
        package="slam_toolbox",
        executable="localization_slam_toolbox_node",
        name="slam_toolbox",
        output="screen",
        parameters=[
            localization_params,
            {
                "use_sim_time": LaunchConfiguration("use_sim_time"),
                "map_file_name": LaunchConfiguration("serialized_map"),
            },
        ],
    )

    command_odom = Node(
        package="sensor_bringup",
        executable="command_odom",
        output="screen",
    )

    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(nav2_bringup_launch),
        launch_arguments={
            "use_sim_time": LaunchConfiguration("use_sim_time"),
            "autostart": LaunchConfiguration("autostart"),
            "params_file": LaunchConfiguration("params_file"),
            "use_composition": "False",
        }.items(),
    )

    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="nav_rviz",
        arguments=["-d", rviz_config],
        output="screen",
        condition=IfCondition(LaunchConfiguration("enable_rviz")),
    )

    return LaunchDescription(
        [
            use_sim_time,
            autostart,
            enable_rviz,
            enable_teleop,
            imu_port,
            agv_host,
            agv_port,
            command_timeout,
            serialized_map,
            params_file,
            sensors,
            command_odom,
            slam_localization,
            nav2,
            rviz,
        ]
    )
