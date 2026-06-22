#!/usr/bin/env python3
from copy import deepcopy

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from visualization_msgs.msg import Marker


class ImuMarkerViz(Node):
    def __init__(self) -> None:
        super().__init__("imu_marker_viz")
        self.declare_parameter("imu_topic", "/imu/data_raw")
        self.declare_parameter("marker_topic", "/imu_marker")
        self.declare_parameter("frame_id", "base_link")
        self.declare_parameter("ns", "imu_viz")
        self.declare_parameter("scale_x", 0.30)
        self.declare_parameter("scale_y", 0.08)
        self.declare_parameter("scale_z", 0.05)
        self.declare_parameter("pos_x", 0.0)
        self.declare_parameter("pos_y", 0.0)
        self.declare_parameter("pos_z", 0.12)
        self.declare_parameter("color_r", 0.15)
        self.declare_parameter("color_g", 0.75)
        self.declare_parameter("color_b", 0.25)
        self.declare_parameter("color_a", 0.90)

        marker_topic = str(self.get_parameter("marker_topic").value)
        imu_topic = str(self.get_parameter("imu_topic").value)

        self.publisher = self.create_publisher(Marker, marker_topic, 10)
        self.create_subscription(Imu, imu_topic, self._on_imu, 10)

        self.marker = Marker()
        self.marker.ns = str(self.get_parameter("ns").value)
        self.marker.id = 0
        self.marker.type = Marker.CUBE
        self.marker.action = Marker.ADD
        self.marker.header.frame_id = str(self.get_parameter("frame_id").value)
        self.marker.pose.position.x = float(self.get_parameter("pos_x").value)
        self.marker.pose.position.y = float(self.get_parameter("pos_y").value)
        self.marker.pose.position.z = float(self.get_parameter("pos_z").value)
        self.marker.pose.orientation.w = 1.0
        self.marker.scale.x = float(self.get_parameter("scale_x").value)
        self.marker.scale.y = float(self.get_parameter("scale_y").value)
        self.marker.scale.z = float(self.get_parameter("scale_z").value)
        self.marker.color.r = float(self.get_parameter("color_r").value)
        self.marker.color.g = float(self.get_parameter("color_g").value)
        self.marker.color.b = float(self.get_parameter("color_b").value)
        self.marker.color.a = float(self.get_parameter("color_a").value)

        self.get_logger().info(
            f"IMU marker visualization ready: {imu_topic} -> {marker_topic}"
        )

    def _on_imu(self, msg: Imu) -> None:
        marker = deepcopy(self.marker)
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.pose.orientation = msg.orientation
        self.publisher.publish(marker)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = ImuMarkerViz()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
