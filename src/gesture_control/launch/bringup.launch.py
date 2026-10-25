"""Full stack: camera + recognition + gesture_to_cmd_vel (+ sim unless sim:=false)."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    control_share = get_package_share_directory("gesture_control")
    recognition_share = get_package_share_directory("gesture_recognition")
    recognizer = LaunchConfiguration("recognizer")
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "recognizer", default_value="mediapipe", description="mediapipe | custom"
            ),
            DeclareLaunchArgument("sim", default_value="true"),
            DeclareLaunchArgument("camera", default_value="true"),
            DeclareLaunchArgument("headless", default_value="false"),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(control_share, "launch", "sim.launch.py")
                ),
                condition=IfCondition(LaunchConfiguration("sim")),
                launch_arguments={"headless": LaunchConfiguration("headless")}.items(),
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(control_share, "launch", "camera.launch.py")
                ),
                condition=IfCondition(LaunchConfiguration("camera")),
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(recognition_share, "launch", "recognition.launch.py")
                ),
                launch_arguments={"recognizer": recognizer}.items(),
            ),
            Node(
                package="gesture_control",
                executable="gesture_to_cmd_vel_node",
                name="gesture_to_cmd_vel_node",
                parameters=[os.path.join(control_share, "config", "gesture_map.yaml")],
                output="screen",
            ),
        ]
    )
