"""Gazebo Harmonic + TurtleBot3 world. headless:=true runs the server only (CI / VM)."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    headless = LaunchConfiguration("headless")
    tb3_gazebo = get_package_share_directory("turtlebot3_gazebo")
    return LaunchDescription(
        [
            DeclareLaunchArgument("headless", default_value="false"),
            SetEnvironmentVariable(
                "TURTLEBOT3_MODEL", os.environ.get("TURTLEBOT3_MODEL", "burger")
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(tb3_gazebo, "launch", "turtlebot3_world.launch.py")
                ),
                # forwarded to turtlebot3_world.launch.py
                launch_arguments={"headless": headless}.items(),
            ),
        ]
    )
