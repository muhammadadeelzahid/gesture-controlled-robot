#!/usr/bin/env bash
# Record the webcam stream for offline development on a headless machine.
# Usage: scripts/record_bag.sh [name]   (run camera.launch.py first)
set -euo pipefail
NAME=${1:-gestures_$(date +%Y%m%d_%H%M%S)}
mkdir -p "$(dirname "$0")/../bags"
ros2 bag record -o "$(dirname "$0")/../bags/$NAME" /image_raw /camera_info
