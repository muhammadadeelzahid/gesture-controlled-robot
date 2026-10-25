"""Full stack: image source + recognition + gesture_to_cmd_vel (+ sim unless sim:=false).

source:=camera uses usb_cam; source:=images images:=<dir> cycles still images instead.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import EqualsSubstitution, LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    control_share = get_package_share_directory("gesture_control")
    recognition_share = get_package_share_directory("gesture_recognition")
    return LaunchDescription(
        [
            DeclareLaunchArgument("sim", default_value="true"),
            DeclareLaunchArgument("source", default_value="camera", description="camera | images"),
            DeclareLaunchArgument(
                "images",
                default_value="",
                description="image files or directories for source:=images",
            ),
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
                condition=IfCondition(EqualsSubstitution(LaunchConfiguration("source"), "camera")),
            ),
            Node(
                package="gesture_recognition",
                executable="image_sequence_node",
                name="image_sequence_node",
                condition=IfCondition(EqualsSubstitution(LaunchConfiguration("source"), "images")),
                parameters=[{"images": LaunchConfiguration("images"), "hold_s": 4.0}],
                output="screen",
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(recognition_share, "launch", "recognition.launch.py")
                ),
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
