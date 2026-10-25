"""launch_testing: fake /gesture drives /cmd_vel; silence stops the robot."""

import time
import unittest

import launch
import launch_ros.actions
import launch_testing.actions
import pytest
import rclpy
from geometry_msgs.msg import TwistStamped

from gesture_msgs.msg import Gesture


@pytest.mark.launch_test
def generate_test_description():
    node = launch_ros.actions.Node(
        package="gesture_control",
        executable="gesture_to_cmd_vel_node",
        parameters=[
            {
                "use_stamped": True,
                "deadman_timeout_s": 0.5,
                "linear_accel": 100.0,
                "angular_accel": 100.0,
                "gesture_labels": ["pointing_up"],
                "gestures.pointing_up": [0.15, 0.0],
            }
        ],
    )
    return launch.LaunchDescription([node, launch_testing.actions.ReadyToTest()]), {"node": node}


class TestCmdVel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rclpy.init()
        cls.node = rclpy.create_node("test_cmd_vel")
        cls.received = []
        cls.node.create_subscription(TwistStamped, "cmd_vel", cls.received.append, 10)
        cls.pub = cls.node.create_publisher(Gesture, "gesture", 10)

    @classmethod
    def tearDownClass(cls):
        cls.node.destroy_node()
        rclpy.shutdown()

    def _spin(self, seconds, publish=None):
        end = time.time() + seconds
        while time.time() < end:
            if publish is not None:
                self.pub.publish(publish)
            rclpy.spin_once(self.node, timeout_sec=0.05)

    def test_gesture_then_timeout(self):
        g = Gesture()
        g.label = "pointing_up"
        g.confidence = 0.99
        self.received.clear()
        self._spin(2.0, publish=g)
        assert self.received, "no /cmd_vel received"
        assert abs(self.received[-1].twist.linear.x - 0.15) < 1e-6

        self.received.clear()
        self._spin(2.0)
        assert self.received[-1].twist.linear.x == 0.0
