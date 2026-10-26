"""Live webcam -> gesture -> /cmd_vel, with no simulator.

Starts the USB camera, the gesture classifier and the cmd_vel control node. Pass overlay:=true
to also run hand_landmarker_node and its /hand/image_annotated skeleton view. The width, height
and framerate arguments lower the camera load on a Raspberry Pi; use_stamped:=false publishes a
plain geometry_msgs/Twist for a robot that expects it.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    control_share = get_package_share_directory("gesture_control")
    recognition_share = get_package_share_directory("gesture_recognition")
    recognition_params = os.path.join(recognition_share, "config", "recognition.yaml")
    gesture_map = os.path.join(control_share, "config", "gesture_map.yaml")

    return LaunchDescription(
        [
            DeclareLaunchArgument("video_device", default_value="/dev/video0"),
            DeclareLaunchArgument("width", default_value="640"),
            DeclareLaunchArgument("height", default_value="480"),
            DeclareLaunchArgument("framerate", default_value="30.0"),
            DeclareLaunchArgument("pixel_format", default_value="mjpeg2rgb"),
            DeclareLaunchArgument("use_stamped", default_value="true"),
            DeclareLaunchArgument(
                "overlay",
                default_value="false",
                description="also run hand_landmarker_node for the /hand/image_annotated view",
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(control_share, "launch", "camera.launch.py")
                ),
                launch_arguments={
                    "video_device": LaunchConfiguration("video_device"),
                    "image_width": LaunchConfiguration("width"),
                    "image_height": LaunchConfiguration("height"),
                    "framerate": LaunchConfiguration("framerate"),
                    "pixel_format": LaunchConfiguration("pixel_format"),
                }.items(),
            ),
            Node(
                package="gesture_recognition",
                executable="hand_landmarker_node",
                name="hand_landmarker_node",
                condition=IfCondition(LaunchConfiguration("overlay")),
                parameters=[recognition_params],
                output="screen",
            ),
            Node(
                package="gesture_recognition",
                executable="gesture_classifier_node",
                name="gesture_classifier_node",
                parameters=[recognition_params],
                output="screen",
            ),
            Node(
                package="gesture_control",
                executable="gesture_to_cmd_vel_node",
                name="gesture_to_cmd_vel_node",
                parameters=[
                    gesture_map,
                    {
                        "use_stamped": ParameterValue(
                            LaunchConfiguration("use_stamped"), value_type=bool
                        )
                    },
                ],
                output="screen",
            ),
        ]
    )
