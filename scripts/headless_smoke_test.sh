#!/usr/bin/env bash
# Headless Gazebo smoke test: start turtlebot3_world without a GUI, publish a
# velocity command and assert that /odom reports motion. Used by CI and on the VM.
set -eo pipefail
export TURTLEBOT3_MODEL=${TURTLEBOT3_MODEL:-burger}
source /opt/ros/jazzy/setup.bash
[ -f install/setup.bash ] && source install/setup.bash

ros2 launch gesture_control sim.launch.py headless:=true &
LAUNCH_PID=$!
trap 'kill $LAUNCH_PID 2>/dev/null; wait $LAUNCH_PID 2>/dev/null || true' EXIT

echo "waiting for /odom ..."
timeout 120 bash -c 'until ros2 topic list | grep -q "^/odom$"; do sleep 2; done'
X0=$(timeout 30 ros2 topic echo /odom --once --field pose.pose.position.x | head -1)
echo "initial x=$X0"
timeout 10 ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/TwistStamped \
  "{header: {frame_id: base_link}, twist: {linear: {x: 0.2}}}" >/dev/null || true
X1=$(timeout 30 ros2 topic echo /odom --once --field pose.pose.position.x | head -1)
echo "final   x=$X1"
python3 - "$X0" "$X1" <<'PY'
import sys
x0, x1 = float(sys.argv[1]), float(sys.argv[2])
assert x1 - x0 > 0.05, f"robot did not move: {x0} -> {x1}"
print("OK: robot moved", round(x1 - x0, 3), "m")
PY
