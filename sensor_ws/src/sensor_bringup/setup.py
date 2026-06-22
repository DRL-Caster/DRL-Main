from glob import glob
import os

from setuptools import find_packages, setup


package_name = "sensor_bringup"


setup(
    name=package_name,
    version="0.0.1",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (os.path.join("share", package_name, "launch"), glob(os.path.join("launch", "*.launch.py"))),
        (os.path.join("share", package_name, "config"), glob(os.path.join("config", "*.yaml"))),
        (os.path.join("share", package_name, "maps"), glob(os.path.join("maps", "*"))),
        (os.path.join("share", package_name, "rviz"), glob(os.path.join("rviz", "*.rviz"))),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="kenbio",
    maintainer_email="kenbio@example.com",
    description="Combined bringup for lidar, IMU, and AGV control.",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "command_odom = sensor_bringup.command_odom:main",
            "imu_marker_viz = sensor_bringup.imu_marker_viz:main",
        ],
    },
)
