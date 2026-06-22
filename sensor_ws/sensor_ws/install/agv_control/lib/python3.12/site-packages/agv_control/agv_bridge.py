#!/usr/bin/env python3
import socket
import struct
import time
from typing import Optional, Tuple

import rclpy
from geometry_msgs.msg import Twist
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from std_msgs.msg import String


class ModbusAgvClient:
    HEARTBEAT_HEAD = 0xBB
    HEARTBEAT_LEN = 34

    def __init__(
        self,
        host: str,
        port: int,
        unit_id: int,
        control_addr: int,
        socket_timeout: float,
        connect_settle_sec: float,
    ) -> None:
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.control_addr = control_addr
        self.socket_timeout = socket_timeout
        self.connect_settle_sec = connect_settle_sec
        self.sock: Optional[socket.socket] = None
        self.tid = 1

    def close(self) -> None:
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None

    def connect(self) -> None:
        if self.sock is not None:
            return
        self.sock = socket.create_connection((self.host, self.port), timeout=self.socket_timeout)
        self.sock.settimeout(self.socket_timeout)
        if self.connect_settle_sec > 0:
            time.sleep(self.connect_settle_sec)

    def send_command(self, value: int) -> None:
        self.connect()
        assert self.sock is not None
        self._flush_socket(self.sock)
        self._write_single_register(self.sock, self.tid, self.control_addr, value)
        self.tid = 1 if self.tid >= 0xFFFF else self.tid + 1

    def _build_write_single_register(self, tid: int, addr: int, value: int) -> bytes:
        return struct.pack(">HHHBBHH", tid, 0, 6, self.unit_id, 0x06, addr, value)

    def _flush_socket(self, sock: socket.socket, max_rounds: int = 20) -> None:
        sock.setblocking(False)
        try:
            for _ in range(max_rounds):
                try:
                    data = sock.recv(4096)
                    if not data:
                        break
                except BlockingIOError:
                    break
        finally:
            sock.setblocking(True)

    def _try_extract_matching_modbus_frame(self, buf: bytearray, expected_tid: int):
        while True:
            if len(buf) >= 1 and buf[0] == self.HEARTBEAT_HEAD:
                if len(buf) < self.HEARTBEAT_LEN:
                    return None
                del buf[:self.HEARTBEAT_LEN]
                continue

            if len(buf) < 7:
                return None

            tid = int.from_bytes(buf[0:2], "big")
            pid = int.from_bytes(buf[2:4], "big")
            length = int.from_bytes(buf[4:6], "big")
            unit_id = buf[6]

            if pid == 0 and 2 <= length <= 260:
                adu_len = 6 + length
                if len(buf) < adu_len:
                    return None
                frame = bytes(buf[:adu_len])
                del buf[:adu_len]
                if tid != expected_tid or unit_id != self.unit_id:
                    continue
                return frame

            del buf[0]

    def _recv_exact_filtered_response(self, sock: socket.socket, expected_tid: int) -> bytes:
        buf = bytearray()
        deadline = time.monotonic() + self.socket_timeout

        while True:
            frame = self._try_extract_matching_modbus_frame(buf, expected_tid)
            if frame is not None:
                return frame

            remain = deadline - time.monotonic()
            if remain <= 0:
                raise TimeoutError(f"timeout waiting for response tid={expected_tid}")

            sock.settimeout(remain)
            chunk = sock.recv(4096)
            if not chunk:
                raise ConnectionError("peer closed connection")
            buf.extend(chunk)

    def _write_single_register(self, sock: socket.socket, tid: int, addr: int, value: int) -> None:
        request = self._build_write_single_register(tid, addr, value)
        sock.sendall(request)
        response = self._recv_exact_filtered_response(sock, expected_tid=tid)

        if len(response) < 12:
            raise RuntimeError(f"response too short: {response.hex(' ')}")

        func = response[7]
        if func == 0x86:
            exc_code = response[8] if len(response) > 8 else None
            raise RuntimeError(f"modbus exception: code={exc_code}, hex={response.hex(' ')}")
        if func != 0x06:
            raise RuntimeError(f"unexpected function: {func}, hex={response.hex(' ')}")

        resp_addr = int.from_bytes(response[8:10], "big")
        resp_value = int.from_bytes(response[10:12], "big")
        if resp_addr != addr or resp_value != value:
            raise RuntimeError(
                f"write echo mismatch: addr={resp_addr}, value={resp_value}, hex={response.hex(' ')}"
            )


class AgvBridge(Node):
    def __init__(self) -> None:
        super().__init__("agv_bridge")

        self.declare_parameter("host", "192.168.1.254")
        self.declare_parameter("port", 1024)
        self.declare_parameter("unit_id", 1)
        self.declare_parameter("control_addr", 4)
        self.declare_parameter("socket_timeout_sec", 5.0)
        self.declare_parameter("connect_settle_sec", 0.5)
        self.declare_parameter("reconnect_interval_sec", 1.0)
        self.declare_parameter("command_timeout_sec", 0.6)
        self.declare_parameter("timer_period_sec", 0.1)
        self.declare_parameter("linear_deadband", 0.05)
        self.declare_parameter("angular_deadband", 0.1)
        self.declare_parameter("initial_mode", "teleop")
        self.declare_parameter("cmd_forward", 1)
        self.declare_parameter("cmd_backward", 2)
        self.declare_parameter("cmd_left", 3)
        self.declare_parameter("cmd_right", 4)
        self.declare_parameter("cmd_stop", 5)

        self.mode = self._validate_mode(self.get_parameter("initial_mode").value)
        self.pending_mode = self.mode
        self.current_command = self.get_parameter("cmd_stop").value
        self.last_sent_command: Optional[int] = self.current_command
        self.next_retry_time = 0.0

        self.nav_twist = Twist()
        self.nav_stamp = None
        self.teleop_twist = Twist()
        self.teleop_stamp = None

        self.client = ModbusAgvClient(
            host=self.get_parameter("host").value,
            port=self.get_parameter("port").value,
            unit_id=self.get_parameter("unit_id").value,
            control_addr=self.get_parameter("control_addr").value,
            socket_timeout=self.get_parameter("socket_timeout_sec").value,
            connect_settle_sec=self.get_parameter("connect_settle_sec").value,
        )

        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.mode_pub = self.create_publisher(String, "/agv/current_mode", qos)
        self.command_pub = self.create_publisher(String, "/agv/current_command", qos)

        self.create_subscription(Twist, "/cmd_vel_nav", self._on_nav_cmd, 10)
        self.create_subscription(Twist, "/cmd_vel", self._on_nav_cmd, 10)
        self.create_subscription(Twist, "/cmd_vel_teleop", self._on_teleop_cmd, 10)
        self.create_subscription(String, "/agv/control_mode", self._on_mode_msg, qos)

        timer_period = self.get_parameter("timer_period_sec").value
        self.timer = self.create_timer(timer_period, self._on_timer)

        self._publish_mode()
        self._publish_command("stop")
        self.get_logger().info(f"AGV bridge ready in {self.mode!r} mode")

    def _validate_mode(self, mode: str) -> str:
        return mode if mode in {"nav", "teleop"} else "teleop"

    def _on_nav_cmd(self, msg: Twist) -> None:
        self.nav_twist = msg
        self.nav_stamp = self.get_clock().now()
        self.get_logger().info(
            f"nav cmd rx linear.x={msg.linear.x:.3f} angular.z={msg.angular.z:.3f}"
        )

    def _on_teleop_cmd(self, msg: Twist) -> None:
        self.teleop_twist = msg
        self.teleop_stamp = self.get_clock().now()
        self.get_logger().info(
            f"teleop cmd rx linear.x={msg.linear.x:.3f} angular.z={msg.angular.z:.3f}"
        )

    def _on_mode_msg(self, msg: String) -> None:
        requested = self._validate_mode(msg.data.strip())
        if requested != msg.data.strip():
            self.get_logger().warning(f"Ignoring invalid mode request: {msg.data!r}")
            return
        self.pending_mode = requested

    def _publish_mode(self) -> None:
        msg = String()
        msg.data = self.mode
        self.mode_pub.publish(msg)

    def _publish_command(self, label: str) -> None:
        msg = String()
        msg.data = label
        self.command_pub.publish(msg)

    def _twist_for_mode(self) -> Tuple[Twist, Optional[rclpy.time.Time]]:
        if self.mode == "nav":
            return self.nav_twist, self.nav_stamp
        return self.teleop_twist, self.teleop_stamp

    def _select_command(self) -> Tuple[int, str]:
        stop = self.get_parameter("cmd_stop").value
        twist, stamp = self._twist_for_mode()
        timeout = Duration(seconds=self.get_parameter("command_timeout_sec").value)

        if stamp is None or (self.get_clock().now() - stamp) > timeout:
            return stop, "stop"

        linear = float(twist.linear.x)
        angular = float(twist.angular.z)
        linear_deadband = float(self.get_parameter("linear_deadband").value)
        angular_deadband = float(self.get_parameter("angular_deadband").value)

        if abs(linear) < linear_deadband and abs(angular) < angular_deadband:
            return stop, "stop"

        if abs(linear) >= abs(angular):
            if linear >= linear_deadband:
                return self.get_parameter("cmd_forward").value, "forward"
            if linear <= -linear_deadband:
                return self.get_parameter("cmd_backward").value, "backward"

        if angular >= angular_deadband:
            return self.get_parameter("cmd_left").value, "left"
        if angular <= -angular_deadband:
            return self.get_parameter("cmd_right").value, "right"
        return stop, "stop"

    def _send_command(self, command: int, label: str) -> None:
        now = time.monotonic()
        if now < self.next_retry_time:
            return

        last_error = None
        for attempt in range(2):
            try:
                self.client.send_command(command)
                self.last_sent_command = command
                self.current_command = command
                self._publish_command(label)
                self.get_logger().info(f"AGV command => {label}")
                return
            except Exception as exc:
                last_error = exc
                self.client.close()
                if attempt == 0:
                    time.sleep(float(self.get_parameter("reconnect_interval_sec").value))

        self.next_retry_time = now + float(self.get_parameter("reconnect_interval_sec").value)
        self.get_logger().error(f"AGV command failed ({label}): {last_error}")

    def _on_timer(self) -> None:
        stop = self.get_parameter("cmd_stop").value

        if self.pending_mode != self.mode:
            if self.last_sent_command != stop:
                self._send_command(stop, "stop")
            self.mode = self.pending_mode
            self._publish_mode()
            self.get_logger().info(f"Switched control mode to {self.mode!r}")

        desired_command, label = self._select_command()
        if desired_command != self.last_sent_command:
            self.get_logger().info(
                f"command select mode={self.mode} desired={label} last={self.last_sent_command}"
            )
            self._send_command(desired_command, label)

    def destroy_node(self) -> bool:
        stop = self.get_parameter("cmd_stop").value
        try:
            if self.last_sent_command != stop:
                self.client.send_command(stop)
        except Exception:
            pass
        self.client.close()
        return super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = AgvBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
