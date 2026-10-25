"""Gazebo Harmonic with the TurtleBot3 world. headless:=true starts the server only."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    AppendEnvironmentVariable,
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    SetEnvironmentVariable,
)
from launch.conditions import UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    tb3_gazebo = get_package_share_directory("turtlebot3_gazebo")
    ros_gz_sim = get_package_share_directory("ros_gz_sim")
    gz_sim = os.path.join(ros_gz_sim, "launch", "gz_sim.launch.py")
    world = os.path.join(tb3_gazebo, "worlds", "turtlebot3_world.world")
    headless = LaunchConfiguration("headless")

    return LaunchDescription(
        [
            DeclareLaunchArgument("headless", default_value="false"),
            DeclareLaunchArgument("x_pose", default_value="-2.0"),
            DeclareLaunchArgument("y_pose", default_value="-0.5"),
            SetEnvironmentVariable(
                "TURTLEBOT3_MODEL", os.environ.get("TURTLEBOT3_MODEL", "burger")
            ),
            AppendEnvironmentVariable("GZ_SIM_RESOURCE_PATH", os.path.join(tb3_gazebo, "models")),
            # server
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(gz_sim),
                launch_arguments={
                    "gz_args": ["-r -s -v2 ", world],
                    "on_exit_shutdown": "true",
                }.items(),
            ),
            # client, skipped when headless
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(gz_sim),
                condition=UnlessCondition(headless),
                launch_arguments={"gz_args": "-g -v2 ", "on_exit_shutdown": "true"}.items(),
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(tb3_gazebo, "launch", "robot_state_publisher.launch.py")
                ),
                launch_arguments={"use_sim_time": "true"}.items(),
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(tb3_gazebo, "launch", "spawn_turtlebot3.launch.py")
                ),
                launch_arguments={
                    "x_pose": LaunchConfiguration("x_pose"),
                    "y_pose": LaunchConfiguration("y_pose"),
                }.items(),
            ),
        ]
    )
