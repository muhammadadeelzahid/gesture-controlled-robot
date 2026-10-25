"""ROS 2 node: /gesture (gesture_msgs/Gesture) -> /cmd_vel (TwistStamped or Twist)."""

from __future__ import annotations

import rclpy
from geometry_msgs.msg import Twist, TwistStamped
from rclpy.node import Node

from gesture_control.velocity import VelocityController, VelocityLimits
from gesture_msgs.msg import Gesture


class GestureToCmdVel(Node):
    def __init__(self) -> None:
        super().__init__("gesture_to_cmd_vel_node")
        self.declare_parameter("use_stamped", True)
        self.declare_parameter("frame_id", "base_link")
        self.declare_parameter("publish_rate_hz", 20.0)
        self.declare_parameter("deadman_timeout_s", 0.5)
        self.declare_parameter("min_confidence", 0.8)
        self.declare_parameter("max_linear", 0.22)
        self.declare_parameter("max_angular", 2.84)
        self.declare_parameter("linear_accel", 0.5)
        self.declare_parameter("angular_accel", 3.0)
        self.declare_parameter(
            "gesture_labels",
            ["open_palm", "fist", "pointing_up", "victory", "thumb_up", "thumb_down"],
        )

        gestures = self._load_gesture_map()
        self.controller = VelocityController(
            gestures=gestures,
            limits=VelocityLimits(
                max_linear=self.get_parameter("max_linear").value,
                max_angular=self.get_parameter("max_angular").value,
                linear_accel=self.get_parameter("linear_accel").value,
                angular_accel=self.get_parameter("angular_accel").value,
            ),
            deadman_timeout_s=self.get_parameter("deadman_timeout_s").value,
            min_confidence=self.get_parameter("min_confidence").value,
        )

        self.use_stamped = self.get_parameter("use_stamped").value
        self.frame_id = self.get_parameter("frame_id").value
        msg_type = TwistStamped if self.use_stamped else Twist
        self.pub = self.create_publisher(msg_type, "cmd_vel", 10)
        self.sub = self.create_subscription(Gesture, "gesture", self._on_gesture, 10)

        self.dt = 1.0 / self.get_parameter("publish_rate_hz").value
        self.timer = self.create_timer(self.dt, self._on_timer)
        self.get_logger().info(f"gesture map: {gestures}; stamped={self.use_stamped}")

    def _load_gesture_map(self) -> dict[str, tuple[float, float]]:
        # Nested YAML maps are flattened by rclpy as 'gestures.<label>' double-array params.
        gestures: dict[str, tuple[float, float]] = {}
        for label in self.get_parameter("gesture_labels").value:
            self.declare_parameter(f"gestures.{label}", [0.0, 0.0])
            lin, ang = self.get_parameter(f"gestures.{label}").value
            gestures[label] = (float(lin), float(ang))
        return gestures

    def _now(self) -> float:
        return self.get_clock().now().nanoseconds * 1e-9

    def _on_gesture(self, msg: Gesture) -> None:
        self.controller.on_gesture(msg.label, msg.confidence, self._now())

    def _on_timer(self) -> None:
        lin, ang = self.controller.step(self._now(), self.dt)
        twist = Twist()
        twist.linear.x = lin
        twist.angular.z = ang
        if self.use_stamped:
            out = TwistStamped()
            out.header.stamp = self.get_clock().now().to_msg()
            out.header.frame_id = self.frame_id
            out.twist = twist
            self.pub.publish(out)
        else:
            self.pub.publish(twist)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = GestureToCmdVel()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
