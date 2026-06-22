#!/usr/bin/env python3
import select
import sys
import termios
import time
import tty

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node


HELP = """
WASD 键盘遥控：
  w：前进
  s：后退
  a：左转
  d：右转
  空格/x：停止
  q：退出
"""


class KeyboardTeleop(Node):
    def __init__(self) -> None:
        super().__init__("keyboard_teleop")
        self.declare_parameter("publish_topic", "/cmd_vel_teleop")
        self.declare_parameter("linear_speed", 1.0)
        self.declare_parameter("angular_speed", 1.0)
        self.declare_parameter("deadman_timeout_sec", 0.35)

        topic = self.get_parameter("publish_topic").value
        self.publisher = self.create_publisher(Twist, topic, 10)
        self.last_key_time = time.monotonic()
        self.active_twist = Twist()
        self.zero_published = False

        self.get_logger().info(HELP.strip())
        self.timer = self.create_timer(0.05, self._on_timer)

    def _read_key(self) -> str:
        readable, _, _ = select.select([sys.stdin], [], [], 0.0)
        if readable:
            return sys.stdin.read(1)
        return ""

    def _publish_twist(self, linear_x: float, angular_z: float) -> None:
        msg = Twist()
        msg.linear.x = linear_x
        msg.angular.z = angular_z
        self.publisher.publish(msg)

    def _on_timer(self) -> None:
        key = self._read_key()
        linear_speed = float(self.get_parameter("linear_speed").value)
        angular_speed = float(self.get_parameter("angular_speed").value)
        timeout = float(self.get_parameter("deadman_timeout_sec").value)

        if key:
            self.last_key_time = time.monotonic()
            self.zero_published = False

            if key == "w":
                self.active_twist.linear.x = linear_speed
                self.active_twist.angular.z = 0.0
            elif key == "s":
                self.active_twist.linear.x = -linear_speed
                self.active_twist.angular.z = 0.0
            elif key == "a":
                self.active_twist.linear.x = 0.0
                self.active_twist.angular.z = angular_speed
            elif key == "d":
                self.active_twist.linear.x = 0.0
                self.active_twist.angular.z = -angular_speed
            elif key in {"x", " "}:
                self.active_twist = Twist()
                self.zero_published = True
            elif key == "q":
                raise KeyboardInterrupt

            self.publisher.publish(self.active_twist)
            return

        if (time.monotonic() - self.last_key_time) > timeout:
            if not self.zero_published:
                self.active_twist = Twist()
                self.publisher.publish(self.active_twist)
                self.zero_published = True
            return

        self.publisher.publish(self.active_twist)


def main(args=None) -> None:
    settings = termios.tcgetattr(sys.stdin)
    rclpy.init(args=args)
    node = KeyboardTeleop()

    try:
        tty.setcbreak(sys.stdin.fileno())
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        node.publisher.publish(Twist())
        node.destroy_node()
        rclpy.shutdown()
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
