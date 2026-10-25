"""hand_landmarker_node + gesture_classifier_node (MediaPipe GestureRecognizer)."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    share = get_package_share_directory("gesture_recognition")
    params = os.path.join(share, "config", "recognition.yaml")
    return LaunchDescription(
        [
            Node(
                package="gesture_recognition",
                executable="hand_landmarker_node",
                name="hand_landmarker_node",
                parameters=[params],
                output="screen",
            ),
            Node(
                package="gesture_recognition",
                executable="gesture_classifier_node",
                name="gesture_classifier_node",
                parameters=[params],
                output="screen",
            ),
        ]
    )
