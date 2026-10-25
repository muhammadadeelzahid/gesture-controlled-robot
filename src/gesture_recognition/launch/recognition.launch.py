"""hand_landmarker_node + gesture_classifier_node. recognizer:=mediapipe|custom"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    share = get_package_share_directory("gesture_recognition")
    params = os.path.join(share, "config", "recognition.yaml")
    recognizer = LaunchConfiguration("recognizer")
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "recognizer", default_value="mediapipe", description="mediapipe | custom"
            ),
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
                parameters=[params, {"recognizer": recognizer}],
                output="screen",
            ),
        ]
    )
