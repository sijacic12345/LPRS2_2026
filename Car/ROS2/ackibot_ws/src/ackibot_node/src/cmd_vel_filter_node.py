#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, TwistStamped


class CmdVelFilterNode(Node):
    """
    Propušta Twist poruke dalje samo ako ima stvarnog inputa (linear ili angular != 0).
    Twist(0,0) se ignoriše — twist_mux ga tretira kao idle i prebacuje na auto.
    """

    def __init__(self):
        super().__init__('cmd_vel_filter_node')

        self.declare_parameter('threshold', 0.01)
        self.threshold = self.get_parameter('threshold').value

        self.sub = self.create_subscription(
            TwistStamped,
            '/cmd_vel_joy_sbc',
            self._cb,
            10
        )

        self.pub = self.create_publisher(
            TwistStamped,
            '/cmd_vel_joy_filtered',
            10
        )

        self.get_logger().info(
            f"CmdVelFilterNode pokrenut. threshold={self.threshold}"
        )

    def _cb(self, msg: TwistStamped):
        lx = msg.twist.linear.x
        ly = msg.twist.linear.y
        az = msg.twist.angular.z

        has_input = (
            abs(lx) > self.threshold or
            abs(ly) > self.threshold or
            abs(az) > self.threshold
        )

        if has_input:
            self.pub.publish(msg)
            self.get_logger().debug(
                f"PROPUŠTA  lx={lx:+.3f}  az={az:+.3f}"
            )
        else:
            self.get_logger().debug("BLOKIRA  Twist(0,0)")


def main(args=None):
    rclpy.init(args=args)
    node = CmdVelFilterNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()