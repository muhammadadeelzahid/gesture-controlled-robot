#!/usr/bin/env bash
# Whole pipeline on a headless machine: still images -> gestures -> cmd_vel -> Gazebo.
# Records /odom, /gesture, /cmd_vel and the annotated image, then renders docs/demo/.
#   IMAGES=dir RECOGNIZER=mediapipe|custom DURATION=seconds KEEP_BAG=1 scripts/demo_headless.sh
set -eo pipefail
cd "$(dirname "$0")/.."
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export TURTLEBOT3_MODEL=${TURTLEBOT3_MODEL:-burger}

IMAGES=${IMAGES:-src/gesture_recognition/test/images}
RECOGNIZER=${RECOGNIZER:-mediapipe}
DURATION=${DURATION:-24}
OUT=${OUT:-bags/demo}
rm -rf "$OUT"

ros2 launch gesture_control bringup.launch.py sim:=true headless:=true \
  source:=images images:="$IMAGES" recognizer:="$RECOGNIZER" &
LAUNCH=$!
trap 'kill $LAUNCH 2>/dev/null; wait $LAUNCH 2>/dev/null || true' EXIT

for t in /odom /gesture /cmd_vel; do
  timeout 180 bash -c "until ros2 topic list | grep -q '^$t\$'; do sleep 2; done"
done
sleep 4

# Background jobs in a non-interactive shell ignore SIGINT, so stop the
# recorder with SIGTERM via timeout. The annotated image stream is about
# 15 MB/s, so keep DURATION short.
timeout --signal=TERM "$DURATION" ros2 bag record -o "$OUT" \
  /odom /gesture /cmd_vel /hand/image_annotated || true
pkill -TERM -f "ros2 bag record" 2>/dev/null || true
sleep 2

python3 scripts/plot_demo.py "$OUT" docs/demo
du -sh "$OUT"
[ -n "$KEEP_BAG" ] || rm -rf "${OUT:?}"
