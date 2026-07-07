#!/usr/bin/env python3

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

import numpy as np
import time
from line_detection import detect_lines_logic

Gst.init(None)


class LaneFollowerNode(Node):

    def __init__(self):
        super().__init__('lane_follower_node')

        # PD parametri (tunable)
        self.declare_parameter('kp', 0.003)
        self.declare_parameter('kd', 0.001)
        self.declare_parameter('base_speed', 0.2)
        self.declare_parameter('max_angular', 0.8)

        self.kp = self.get_parameter('kp').value
        self.kd = self.get_parameter('kd').value
        self.base_speed = self.get_parameter('base_speed').value
        self.max_angular = self.get_parameter('max_angular').value

        self.prev_offset = 0

        # Debug state
        self.frame_count = 0
        self.frames_with_line = 0
        self.frames_no_line = 0
        self.t_start = time.time()
        self.t_last_status = self.t_start

        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel_auto', 10)

        # Status timer — svake 2 sekunde ispisi sažetak
        self.create_timer(2.0, self._log_status)

        # GStreamer capture pipeline (libcamera za RPi5)
        self.capture_pipe = Gst.parse_launch(
            "libcamerasrc ! "
            "video/x-raw,width=640,height=480,format=BGR ! "
            "appsink name=mysink emit-signals=True sync=False max-buffers=1 drop=True"
        )

        self.sink = self.capture_pipe.get_by_name("mysink")
        self.sink.connect("new-sample", self._on_new_sample)

        self.capture_pipe.set_state(Gst.State.PLAYING)
        self.get_logger().info("LaneFollowerNode pokrenut.")

    def _on_new_sample(self, sink):
        sample = sink.emit("pull-sample")
        if sample is None:
            return Gst.FlowReturn.ERROR

        buf = sample.get_buffer()
        result, mapinfo = buf.map(Gst.MapFlags.READ)
        if not result:
            return Gst.FlowReturn.ERROR

        frame = np.ndarray((480, 640, 3), buffer=mapinfo.data, dtype=np.uint8).copy()
        buf.unmap(mapinfo)

        self.frame_count += 1
        _, offset = detect_lines_logic(frame)

        if offset != 0:
            self.frames_with_line += 1
        else:
            self.frames_no_line += 1
            self.get_logger().warn(
                f"[frame {self.frame_count}] Linija nije detektovana!"
            )

        self._publish_cmd(offset)

        return Gst.FlowReturn.OK

    def _publish_cmd(self, offset: int):
        # PD korektor
        derivative = offset - self.prev_offset
        angular = -(self.kp * offset + self.kd * derivative)
        angular = float(np.clip(angular, -self.max_angular, self.max_angular))
        self.prev_offset = offset

        msg = Twist()
        msg.linear.x = self.base_speed if offset != 0 else 0.0
        msg.angular.z = angular

        self.cmd_pub.publish(msg)

        self.get_logger().info(
            f"offset={offset:+4d}px  angular={angular:+.3f}rad/s  "
            f"linear={msg.linear.x:.2f}m/s"
        )

    def _log_status(self):
        now = time.time()
        elapsed = now - self.t_last_status
        self.t_last_status = now

        total = self.frames_with_line + self.frames_no_line
        if total == 0:
            self.get_logger().warn("Status: 0 frejmova primljeno — kamera ne radi?")
            return

        fps = total / elapsed
        detection_rate = 100.0 * self.frames_with_line / total

        self.get_logger().info(
            f"--- STATUS ---  "
            f"FPS: {fps:.1f}  |  "
            f"Detekcija: {detection_rate:.0f}%  "
            f"({self.frames_with_line}/{total})  |  "
            f"kp={self.kp}  kd={self.kd}  base_speed={self.base_speed}"
        )

        # Reset za sledeci interval
        self.frames_with_line = 0
        self.frames_no_line = 0

    def destroy_node(self):
        self.capture_pipe.set_state(Gst.State.NULL)
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = LaneFollowerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()