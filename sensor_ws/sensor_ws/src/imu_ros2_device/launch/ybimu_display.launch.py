from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration

from launch_ros.actions import Node

import os


def generate_launch_description():

    package_share = get_package_share_directory('imu_ros2_device')
    default_rviz_config_path = os.path.join(package_share, 'rviz', 'ybimu.rviz')

    rviz_arg = DeclareLaunchArgument(name='rvizconfig', default_value=str(default_rviz_config_path),
                                     description='Absolute path to rviz config file')
    enable_rviz_arg = DeclareLaunchArgument(
        name='enable_rviz',
        default_value='false',
        description='Launch rviz2 when true'
    )
    enable_filter_arg = DeclareLaunchArgument(
        name='enable_filter',
        default_value='false',
        description='Launch imu_filter_madgwick when true'
    )
    port_arg = DeclareLaunchArgument(
        name='port_name',
        default_value='/dev/ttyUSB1',
        description='Serial port used by the IMU'
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', LaunchConfiguration('rvizconfig')],
        condition=IfCondition(LaunchConfiguration('enable_rviz')),
    )

    device_node = Node(
        package='imu_ros2_device',
        executable='ybimu_driver',
        parameters=[{'port_name': LaunchConfiguration('port_name')}],
    )

    imu_filter_config = os.path.join(              
        get_package_share_directory('imu_ros2_device'),
        'config',
        'imu_filter_param.yaml'
    )

    imu_filter_node = Node(
        package='imu_filter_madgwick',
        executable='imu_filter_madgwick_node',
        parameters=[imu_filter_config],
        condition=IfCondition(LaunchConfiguration('enable_filter')),
    )

    return LaunchDescription([
        rviz_arg,
        enable_rviz_arg,
        enable_filter_arg,
        port_arg,
        rviz_node,
        device_node,
        imu_filter_node,
    ])

