# Gesture Controlled Robot

Drive a TurtleBot3 in Gazebo Harmonic with hand gestures from a webcam.

```
usb_cam -> hand_landmarker_node -> gesture_classifier_node -> gesture_to_cmd_vel_node -> /cmd_vel -> TurtleBot3
```

**Stack:** ROS 2 Jazzy Jalisco (LTS), Gazebo Harmonic, TurtleBot3 burger, MediaPipe Tasks
`HandLandmarker` and `GestureRecognizer`, OpenCV, Docker devcontainer. Runs on x86_64 and
arm64 (mediapipe 1.x has wheels for both).

See [docs/PLAN.md](docs/PLAN.md) for the design, work plan and reasoning, and
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the node and topic layout.

## Quick start (Docker)

```bash
scripts/download_models.sh                 # fetch MediaPipe .task models (not in git)
docker compose -f docker/docker-compose.yml build
docker compose -f docker/docker-compose.yml run --rm dev     # headless shell
# inside the container:
colcon build --symlink-install && source install/setup.bash
pytest                                     # unit tests + launch tests
```

On a machine with a display and webcam:

```bash
xhost +local:docker
docker compose -f docker/docker-compose.yml run --rm demo
ros2 launch gesture_control bringup.launch.py
ros2 run rqt_image_view rqt_image_view /hand/image_annotated           # optional overlay
```

Useful launch arguments for `bringup.launch.py`: `sim:=false` (real robot), `headless:=true`
(no Gazebo client), `source:=images images:=<dir>` (still images instead of a camera).

## Gesture map

| Label | Action | linear.x | angular.z |
|---|---|---|---|
| open_palm, fist | stop | 0 | 0 |
| pointing_up | forward | 0.15 | 0 |
| victory | turn left | 0 | 0.6 |
| thumb_up | turn right | 0 | -0.6 |
| thumb_down | reverse | -0.10 | 0 |

Edit `src/gesture_control/config/gesture_map.yaml` to change it. The control node zeroes the
command 0.5 s after the last gesture, ramps with an acceleration limit and clamps to the
burger's limits.

## Status

Verified in CI (x86_64): lint, pure-python unit tests, colcon build, the launch tests and the
recognition launch test over the still-image fixtures. Still to do with a webcam and a
display: a fist image fixture and threshold tuning on live frames.

## Native install (Ubuntu 24.04)

```bash
sudo apt install ros-jazzy-desktop-full ros-jazzy-turtlebot3-gazebo ros-jazzy-turtlebot3-teleop \
                 ros-jazzy-usb-cam ros-jazzy-cv-bridge ros-jazzy-twist-mux python3-colcon-common-extensions
pip install -r requirements.txt --break-system-packages
```

## Why Jazzy and not Lyrical?

Lyrical Luth (May 2026) is the newest LTS but targets Ubuntu 26.04, and TurtleBot3 has no Lyrical release yet.
Jazzy is LTS until May 2029, runs natively on Ubuntu 24.04, and has TurtleBot3 2.3.x packages. Migrating later
means changing the Docker base image and apt prefix; the nodes themselves are plain rclpy.
