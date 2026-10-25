# Gesture Controlled Robot (ROS 2 Jazzy)

Drive a TurtleBot3 in Gazebo Harmonic with hand gestures from a webcam.

```
usb_cam -> hand_landmarker_node -> gesture_classifier_node -> gesture_to_cmd_vel_node -> /cmd_vel -> TurtleBot3
            (MediaPipe Tasks)      (MediaPipe GestureRecognizer     (deadman, ramp, clamp)
                                    or custom Keras 3 -> LiteRT)
```

**Stack:** ROS 2 Jazzy Jalisco (LTS), Gazebo Harmonic, TurtleBot3 burger, MediaPipe Tasks `HandLandmarker`,
Keras 3 training -> `.tflite` inference with LiteRT (`ai-edge-litert`), OpenCV, Docker devcontainer.

See [docs/PLAN.md](docs/PLAN.md) for the full design, phases and rationale.

## Quick start (Docker)

```bash
scripts/download_models.sh                 # fetch MediaPipe .task models (not in git)
docker compose -f docker/docker-compose.yml build
docker compose -f docker/docker-compose.yml run --rm dev     # headless shell (this VM / CI)
# inside the container:
colcon build --symlink-install && source install/setup.bash
pytest
```

On a machine with a display and webcam:

```bash
xhost +local:docker
docker compose -f docker/docker-compose.yml run --rm demo
ros2 launch gesture_control bringup.launch.py recognizer:=mediapipe   # or recognizer:=custom
```

## Gesture map

| Gesture | Action |
|---|---|
| open palm / fist | stop |
| pointing up | forward |
| victory | turn left |
| thumb up | turn right |
| thumb down | reverse |

Edit `src/gesture_control/config/gesture_map.yaml` to change it.

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
