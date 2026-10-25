"""launch_testing: still images -> hand landmarker -> classifier -> /gesture.

Each test image is shown for a few seconds; the most common /gesture label
seen while it is up must match the label in its file name.
"""

import os
import time
import unittest
from collections import Counter, defaultdict

import launch
import launch_ros.actions
import launch_testing.actions
import pytest
import rclpy
from ament_index_python.packages import get_package_share_directory
from std_msgs.msg import String

from gesture_msgs.msg import Gesture

SHARE = get_package_share_directory("gesture_recognition")
IMAGES = os.path.join(SHARE, "test", "images")
HOLD_S = 4.0
# fist has no image fixture yet, see test/images/SOURCES.md
EXPECTED = {
    "open_palm": "open_palm",
    "pointing_up": "pointing_up",
    "victory": "victory",
    "thumb_up": "thumb_up",
    "thumb_down": "thumb_down",
}


@pytest.mark.launch_test
def generate_test_description():
    params = os.path.join(SHARE, "config", "recognition.yaml")
    nodes = [
        launch_ros.actions.Node(
            package="gesture_recognition",
            executable="image_sequence_node",
            parameters=[{"images": IMAGES, "hold_s": HOLD_S, "rate_hz": 10.0}],
        ),
        launch_ros.actions.Node(
            package="gesture_recognition",
            executable="hand_landmarker_node",
            parameters=[params],
        ),
        launch_ros.actions.Node(
            package="gesture_recognition",
            executable="gesture_classifier_node",
            parameters=[params, {"recognizer": os.environ.get("RECOGNIZER", "mediapipe")}],
        ),
    ]
    return launch.LaunchDescription([*nodes, launch_testing.actions.ReadyToTest()]), {}


class TestRecognition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rclpy.init()
        cls.node = rclpy.create_node("test_recognition")
        cls.current = None
        cls.seen = defaultdict(Counter)

        def on_name(msg):
            cls.current = msg.data

        def on_gesture(msg):
            if cls.current is not None:
                cls.seen[cls.current][msg.label] += 1

        cls.node.create_subscription(String, "image_sequence/name", on_name, 10)
        cls.node.create_subscription(Gesture, "gesture", on_gesture, 10)

    @classmethod
    def tearDownClass(cls):
        cls.node.destroy_node()
        rclpy.shutdown()

    def test_each_image_is_recognised(self):
        end = time.time() + HOLD_S * (len(EXPECTED) + 1.5)
        while time.time() < end:
            rclpy.spin_once(self.node, timeout_sec=0.1)
        for stem, label in EXPECTED.items():
            counts = self.seen[stem]
            assert counts, f"no /gesture seen while {stem} was shown"
            # drop the "none" frames the majority vote emits while the image changes
            counts.pop("none", None)
            assert counts, f"only 'none' seen for {stem}"
            top = counts.most_common(1)[0][0]
            assert top == label, f"{stem}: expected {label}, got {dict(counts)}"
