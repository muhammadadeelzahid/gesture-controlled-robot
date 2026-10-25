#!/usr/bin/env bash
set -e
source /opt/ros/jazzy/setup.bash
[ -f /ws/install/setup.bash ] && source /ws/install/setup.bash
export TURTLEBOT3_MODEL=${TURTLEBOT3_MODEL:-burger}
exec "$@"
