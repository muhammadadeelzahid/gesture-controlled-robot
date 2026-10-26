"""Webcam -> /image_raw via usb_cam."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("video_device", default_value="/dev/video0"),
            DeclareLaunchArgument("image_width", default_value="640"),
            DeclareLaunchArgument("image_height", default_value="480"),
            DeclareLaunchArgument("framerate", default_value="30.0"),
            DeclareLaunchArgument("pixel_format", default_value="mjpeg2rgb"),
            Node(
                package="usb_cam",
                executable="usb_cam_node_exe",
                name="usb_cam",
                parameters=[
                    {
                        "video_device": LaunchConfiguration("video_device"),
                        "image_width": ParameterValue(
                            LaunchConfiguration("image_width"), value_type=int
                        ),
                        "image_height": ParameterValue(
                            LaunchConfiguration("image_height"), value_type=int
                        ),
                        "framerate": ParameterValue(
                            LaunchConfiguration("framerate"), value_type=float
                        ),
                        "pixel_format": LaunchConfiguration("pixel_format"),
                        "camera_name": "webcam",
                        "camera_info_url": "",
                    }
                ],
                output="screen",
            ),
        ]
    )
