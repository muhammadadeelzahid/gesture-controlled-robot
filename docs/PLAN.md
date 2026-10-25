# Project plan

Drive a TurtleBot3 in Gazebo with hand gestures from a webcam, on a 2026 LTS stack.

```
usb_cam /image_raw -> hand_landmarker_node -> /hand/landmarks -> gesture_classifier_node -> /gesture -> gesture_to_cmd_vel_node -> /cmd_vel -> TurtleBot3 (Gazebo Harmonic)
```

## 1. Stack

| Layer | Choice | Reason |
|---|---|---|
| ROS | ROS 2 Jazzy Jalisco (LTS, supported to May 2029) | Native on Ubuntu 24.04. TurtleBot3 2.3.x is released for Jazzy. Lyrical Luth (May 2026 LTS) targets Ubuntu 26.04 and has no TurtleBot3 packages yet; moving later is a base-image change since the nodes are plain rclpy. |
| Simulator | Gazebo Harmonic via ros_gz | Paired with Jazzy; turtlebot3_gazebo 2.3.x targets it. |
| Robot | TurtleBot3 burger, turtlebot3_world | Lightest model. On Jazzy its /cmd_vel is geometry_msgs/TwistStamped; the control node has a use_stamped parameter to fall back to Twist. |
| Camera | usb_cam publishing /image_raw | Keeps perception off the hardware; the whole pipeline runs from a rosbag on a headless machine. |
| Hand tracking | MediaPipe Tasks HandLandmarker (mediapipe 1.1, Python 3.12), VIDEO mode, one hand | Current API; mp.solutions is deprecated. Model files are fetched by scripts/download_models.sh and not committed. mediapipe 1.x ships x86_64 and aarch64 wheels, so perception runs on ARM boards too. |
| Recogniser | MediaPipe GestureRecognizer task (pre-trained) | Full demo with no training, runs over /image_raw |
| Packaging | colcon, ament_python nodes, ament_cmake message package, Python launch files, YAML parameters | Standard ROS 2 layout. |
| Dev environment | Docker from the multi-arch ros:jazzy image, compose services dev and demo, devcontainer | Same Dockerfile on arm64 and x86_64. Native install is documented in the README. |
| Checks | ruff, pytest, launch_testing, GitHub Actions | landmarks.py and velocity.py have no ROS imports and are tested with plain pytest. |

## 2. Machines

| | Dev box (VM) | Demo box (laptop) |
|---|---|---|
| Hardware | aarch64, 2 vCPU, 3 GB RAM, no GPU, no display, no webcam | display, webcam |
| Used for | code, unit tests, CI | Gazebo GUI, live camera, demo recording |
| Compose service | dev | demo |

The whole pipeline runs on the dev box from a rosbag or from still images; only the Gazebo GUI and the live webcam need the demo box. Camera data moves to the dev box as rosbags (scripts/record_bag.sh).

## 3. Layout

```
.devcontainer/              VS Code devcontainer on the compose dev service
.github/workflows/ci.yml    lint, colcon build, pytest, colcon test, headless Gazebo smoke test
docker/                     Dockerfile, docker-compose.yml, entrypoint.sh
src/gesture_msgs/           Gesture.msg (header, label, confidence)
src/gesture_recognition/    hand_landmarker_node, gesture_classifier_node, landmarks.py, launch, config, models/
src/gesture_control/        gesture_to_cmd_vel_node, velocity.py, gesture_map.yaml, sim/camera/bringup launch
scripts/                    download_models.sh, record_bag.sh
docs/                       PLAN.md, ARCHITECTURE.md
```

## 4. Topics

| Topic | Type | Notes |
|---|---|---|
| /image_raw | sensor_msgs/Image | 640x480 at 30 FPS |
| /hand/landmarks | std_msgs/Float32MultiArray | 63 floats: wrist-relative, scale-normalised, left hand mirrored |
| /hand/image_annotated | sensor_msgs/Image | debug overlay, published only when subscribed |
| /gesture | gesture_msgs/Gesture | majority vote over 7 frames (at least 5 agree), confidence gate 0.8, otherwise "none" |
| /cmd_vel | geometry_msgs/TwistStamped | deadman 0.5 s, acceleration ramp, clamped to burger limits (0.22 m/s, 2.84 rad/s) |

Gesture map (src/gesture_control/config/gesture_map.yaml):

| Gesture | Action | linear.x | angular.z |
|---|---|---|---|
| open_palm, fist | stop | 0 | 0 |
| pointing_up | forward | 0.15 | 0 |
| victory | turn left | 0 | 0.6 |
| thumb_up | turn right | 0 | -0.6 |
| thumb_down | reverse | -0.10 | 0 |

## 5. Work plan

### 5.1 Simulation baseline (demo box, about half a day)
- Done: the burger bridge config maps /cmd_vel as geometry_msgs/TwistStamped, so use_stamped defaults to true.
- ros2 launch gesture_control sim.launch.py on the demo box, then drive with turtlebot3_teleop.
- Done when: robot moves from teleop.

### 5.2 Camera and hand landmarks
- Done: image_sequence_node stands in for the camera; the landmarker runs on arm64 at about 10 ms per 640x480 frame.
- camera.launch.py on the demo box; record a two minute bag of varied gestures and copy it to the dev box.
- hand_landmarker_node overlay visible in rqt_image_view at 20 FPS or better on the demo box.
- Done when: ros2 topic hz /hand/landmarks matches the camera rate.

### 5.3 End to end with the MediaPipe baseline (first demo)
- Done: recognition launch test (five still images to /gesture) and the cmd_vel launch test pass in CI.
- Done: confidence gates set to 0.6 (classifier) and 0.5 (control) from measured MediaPipe scores.
- bringup.launch.py on the demo box with the webcam; tune window, min_votes, speeds. Check that STOP lands within 0.5 s and that the robot does not move when the hand leaves the frame.

### 5.4 Polish and release
- Latency measurement (Gesture stamp to cmd_vel stamp); optional twist_mux so keyboard teleop overrides gestures.
- README demo GIF, run instructions for both machines, native install notes. Tag v1.0.0.

### Later
- Real TurtleBot3 (perception on the laptop, shared ROS_DOMAIN_ID with the robot).
- Dynamic gestures (swipes) with a small 1D CNN over landmark sequences.
- Move to Lyrical Luth once TurtleBot3 packages are released.

## 6. Risks

| Risk | Handling |
|---|---|
| Twist vs TwistStamped mismatch on /cmd_vel | use_stamped parameter; both types bridge to Gazebo through ros_gz. |
| Webcam or X11 inside Docker on the demo box | demo compose service passes /dev/video0, DISPLAY and /tmp/.X11-unix; native install as fallback. |
| pip pulling numpy 2 over the Ubuntu numpy and breaking cv_bridge | constraints.txt pins numpy below 2 (CI failed on this once). |
| Mirrored webcam flips handedness | frame is mirrored before detection; left-hand landmarks are mirrored in normalize_landmarks. |
| Gesture flicker making the robot jerk | majority vote, acceleration ramp, deadman timeout. |
| Dev box too weak for Gazebo | only headless gz sim -s on the dev box; GUI work on the demo box. |

## 7. Checks

- Dev box: docker compose -f docker/docker-compose.yml run --rm dev, then colcon build --symlink-install, source install/setup.bash, pytest, colcon test.
- Demo box: docker compose -f docker/docker-compose.yml run --rm demo, then ros2 launch gesture_control bringup.launch.py and drive through turtlebot3_world.
- CI on every push: lint, pure-python unit tests, build, unit and launch tests.
