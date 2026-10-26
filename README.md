# Gesture Controlled Robot

Drive a TurtleBot3 in Gazebo Harmonic with hand gestures from a webcam.

```
usb_cam -> hand_landmarker_node -> gesture_classifier_node -> gesture_to_cmd_vel_node -> /cmd_vel -> TurtleBot3
```

Built on ROS 2 Jazzy Jalisco with Gazebo Harmonic and a TurtleBot3 burger. Perception uses the
MediaPipe Tasks `HandLandmarker` and `GestureRecognizer` with OpenCV, and the dev environment is a
Docker devcontainer. mediapipe 1.x ships wheels for both x86_64 and arm64, so the stack runs on
either.

See [docs/plan.md](docs/plan.md) for the design, work plan and reasoning, and
[docs/architecture.md](docs/architecture.md) for the node and topic layout.

## Quick start

Everything below runs in the Docker dev image, which needs no camera or display.

```bash
scripts/download_models.sh                 # fetch the MediaPipe .task models, which are not committed
docker compose -f docker/docker-compose.yml build
docker compose -f docker/docker-compose.yml run --rm dev
# inside the container:
colcon build --symlink-install && source install/setup.bash
pytest                                     # unit and launch tests
```

On a machine with a display and a webcam, use the demo service instead:

```bash
xhost +local:docker
docker compose -f docker/docker-compose.yml run --rm demo
ros2 launch gesture_control bringup.launch.py
ros2 run rqt_image_view rqt_image_view /hand/image_annotated
```

bringup.launch.py takes a few arguments: `sim:=false` for a real robot, `headless:=true` to skip the
Gazebo client, and `source:=images images:=<dir>` to replay still images instead of a camera.

## Gesture map

| Label | Action | linear.x | angular.z |
|---|---|---|---|
| open_palm, fist | stop | 0 | 0 |
| pointing_up | forward | 0.15 | 0 |
| victory | turn left | 0 | 0.6 |
| thumb_up | turn right | 0 | -0.6 |
| thumb_down | reverse | -0.10 | 0 |

Edit `src/gesture_control/config/gesture_map.yaml` to change it. The control node zeroes the command
0.5 s after the last gesture, ramps under an acceleration limit and clamps to the burger's limits.

## Status

CI on x86_64 covers lint, the pure-python unit tests, a colcon build, and the launch tests over the
still-image fixtures. Still to do with a webcam and a display: a fist image fixture and threshold
tuning on live frames.

## Native install on Ubuntu 24.04

```bash
sudo apt install ros-jazzy-desktop-full ros-jazzy-turtlebot3-gazebo ros-jazzy-turtlebot3-teleop \
                 ros-jazzy-usb-cam ros-jazzy-cv-bridge ros-jazzy-twist-mux python3-colcon-common-extensions
pip install -r requirements.txt --break-system-packages
```

## Why Jazzy and not Lyrical?

Lyrical Luth, from May 2026, is the newest LTS, but it targets Ubuntu 26.04 and TurtleBot3 has no
Lyrical release yet. Jazzy is an LTS until May 2029, runs natively on Ubuntu 24.04 and has TurtleBot3
2.3.x packages. Migrating later means changing the Docker base image and apt prefix, while the nodes
themselves stay plain rclpy.
