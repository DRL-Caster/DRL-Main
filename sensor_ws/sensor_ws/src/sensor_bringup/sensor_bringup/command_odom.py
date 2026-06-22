#!/usr/bin/env python3
import math

import rclpy
from geometry_msgs.msg import Quaternion, TransformStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from std_msgs.msg import String
from tf2_ros import TransformBroadcaster


def yaw_to_quaternion(yaw: float) -> Quaternion:
    q = Quaternion()
    q.z = math.sin(yaw * 0.5)
    q.w = math.cos(yaw * 0.5)
    return q


class CommandOdometry(Node):
    def __init__(self) -> None:
        super().__init__("command_odom")
        self.declare_parameter("command_topic", "/agv/current_command")
        self.declare_parameter("odom_topic", "/odom")
        self.declare_parameter("odom_frame", "odom")
        self.declare_parameter("base_frame", "base_link")
        self.declare_parameter("publish_tf", True)
        self.declare_parameter("update_rate_hz", 20.0)
        self.declare_parameter("forward_speed_mps", 0.20)
        self.declare_parameter("backward_speed_mps", 0.16)
        self.declare_parameter("turn_rate_rps", 0.75)

        self.command = "stop"
        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0
        self.linear_velocity = 0.0
        self.angular_velocity = 0.0
        self.last_time = self.get_clock().now()

        self.odom_pub = self.create_publisher(
            Odometry, str(self.get_parameter("odom_topic").value), 10
        )
        self.tf_broadcaster = TransformBroadcaster(self) if self.get_parameter("publish_tf").value else None
        self.create_subscription(
            String, str(self.get_parameter("command_topic").value), self._on_command, 10
        )

        update_rate = float(self.get_parameter("update_rate_hz").value)
        self.create_timer(1.0 / update_rate, self._on_timer)
        self.get_logger().info("Command odometry ready")

    def _on_command(self, msg: String) -> None:
        self.command = msg.data.strip().lower()

    def _velocities_for_command(self) -> tuple[float, float]:
        forward_speed = float(self.get_parameter("forward_speed_mps").value)
        backward_speed = float(self.get_parameter("backward_speed_mps").value)
        turn_rate = float(self.get_parameter("turn_rate_rps").value)

        if self.command == "forward":
            return forward_speed, 0.0
        if self.command == "backward":
            return -backward_speed, 0.0
        if self.command == "left":
            return 0.0, turn_rate
        if self.command == "right":
            return 0.0, -turn_rate
        return 0.0, 0.0

    def _on_timer(self) -> None:
        now = self.get_clock().now()
        dt = (now - self.last_time).nanoseconds / 1e9
        self.last_time = now
        if dt <= 0.0:
            return

        self.linear_velocity, self.angular_velocity = self._velocities_for_command()
        self.yaw += self.angular_velocity * dt
        self.x += self.linear_velocity * math.cos(self.yaw) * dt
        self.y += self.linear_velocity * math.sin(self.yaw) * dt

        quat = yaw_to_quaternion(self.yaw)
        odom_frame = str(self.get_parameter("odom_frame").value)
        base_frame = str(self.get_parameter("base_frame").value)

        odom = Odometry()
        odom.header.stamp = now.to_msg()
        odom.header.frame_id = odom_frame
        odom.child_frame_id = base_frame
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.orientation = quat
        odom.twist.twist.linear.x = self.linear_velocity
        odom.twist.twist.angular.z = self.angular_velocity
        self.odom_pub.publish(odom)

        if self.tf_broadcaster is not None:
            transform = TransformStamped()
            transform.header.stamp = now.to_msg()
            transform.header.frame_id = odom_frame
            transform.child_frame_id = base_frame
            transform.transform.translation.x = self.x
            transform.transform.translation.y = self.y
            transform.transform.rotation = quat
            self.tf_broadcaster.sendTransform(transform)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = CommandOdometry()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
