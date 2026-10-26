# Gesture Controlled Robot

Drive a TurtleBot3 in Gazebo Harmonic with hand gestures from a webcam.

```
usb_cam -> hand_landmarker_node -> gesture_classifier_node -> gesture_to_cmd_vel_node -> /cmd_vel -> TurtleBot3
```

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

`bringup.launch.py` also drives the full stack: `sim:=false` for a real robot, `headless:=true` to
skip the Gazebo client, and `source:=images images:=<dir>` to replay still images instead of a camera.

## Run from a webcam

`robot.launch.py` runs the live pipeline with no simulator. Verify with `ros2 topic echo /cmd_vel`.
Add `overlay:=true` for the `/hand/image_annotated` skeleton view, `use_stamped:=false` for plain
`Twist`.

### Ubuntu computer

```bash
xhost +local:docker
docker compose -f docker/docker-compose.yml run --rm demo
colcon build --symlink-install && source install/setup.bash
ros2 launch gesture_control robot.launch.py overlay:=true
```

### Raspberry Pi 4 (Ubuntu 24.04 Server, arm64)

```bash
sudo apt install ros-jazzy-ros-base ros-jazzy-usb-cam ros-jazzy-cv-bridge \
                 ros-jazzy-image-transport python3-colcon-common-extensions v4l-utils
pip install -c constraints.txt -r requirements.txt --break-system-packages
scripts/download_models.sh
colcon build --symlink-install --parallel-workers 1 && source install/setup.bash
ros2 launch gesture_control robot.launch.py width:=320 height:=240 framerate:=15
```

Knobs if it lags: `framerate:=10`, `pixel_format:=yuyv`, or lower `window`/`min_votes` in
`src/gesture_recognition/config/recognition.yaml`.

## Architecture

```
+----------+  /image_raw   +----------------------+ /hand/landmarks +--------------------------+ /gesture +------------------------+ /cmd_vel +--------------+
| usb_cam  +-------------->| hand_landmarker_node +---------------->| gesture_classifier_node  +--------->| gesture_to_cmd_vel_node+--------->| TurtleBot3   |
| webcam   |               | MediaPipe HandLandm. |                 | MediaPipe Gesture task   |          | deadman · ramp · clamp |          | Gazebo sim   |
+----------+               +----------+-----------+                 +--------------------------+          +------------------------+          +--------------+
                                      | /hand/image_annotated debug overlay, published only when subscribed
```

`gesture_msgs` is an ament_cmake package, while `gesture_recognition` and `gesture_control` are
ament_python. `landmarks.py` and `velocity.py` have no ROS imports, so plain pytest covers them.

## Stack

| Layer | Choice |
|---|---|
| ROS | ROS 2 Jazzy Jalisco |
| Simulator | Gazebo Harmonic via ros_gz |
| Robot | TurtleBot3 burger, turtlebot3_world |
| Camera | usb_cam |
| Hand tracking | MediaPipe Tasks HandLandmarker, mediapipe 1.1 |
| Recogniser | MediaPipe GestureRecognizer task |
| Packaging | colcon, ament_python, ament_cmake |
| Dev environment | Docker from the ros:jazzy image |
| Checks | ruff, pytest, launch_testing, GitHub Actions |

## Topics

| Topic | Type | Notes |
|---|---|---|
| `/image_raw` | `sensor_msgs/Image` | 640x480 at 30 FPS from usb_cam, replayable from a rosbag |
| `/hand/landmarks` | `std_msgs/Float32MultiArray` | 63 floats: wrist-relative, scale-normalised, left hand mirrored |
| `/hand/image_annotated` | `sensor_msgs/Image` | skeleton overlay for rqt_image_view, published only when subscribed |
| `/gesture` | `gesture_msgs/Gesture` | label after a majority vote over 7 frames with at least 5 agreeing, then a confidence gate |
| `/cmd_vel` | `geometry_msgs/TwistStamped` | the Jazzy TurtleBot3 default; deadman 0.5 s, acceleration ramp, clamped to 0.22 m/s and 2.84 rad/s |

## Layout

```
.devcontainer/              VS Code devcontainer on the compose dev service
.github/workflows/ci.yml    lint, unit tests, colcon build and colcon test
docker/                     Dockerfile, docker-compose.yml, entrypoint.sh
src/gesture_msgs/           Gesture.msg with header, label and confidence
src/gesture_recognition/    hand_landmarker_node, gesture_classifier_node, landmarks.py, launch, config, models
src/gesture_control/        gesture_to_cmd_vel_node, velocity.py, gesture_map.yaml, sim/camera/bringup launch
scripts/                    download_models.sh, record_bag.sh
```

## Gesture map

| Label | Action | linear.x | angular.z |
|---|---|---|---|
| open_palm, fist | stop | 0 | 0 |
| pointing_up | forward | 0.15 | 0 |
| victory | turn left | 0 | 0.6 |
| thumb_up | turn right | 0 | -0.6 |
| thumb_down | reverse | -0.10 | 0 |

Edit `src/gesture_control/config/gesture_map.yaml` to change the mapping.

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
