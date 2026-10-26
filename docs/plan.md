# Project plan

Drive a TurtleBot3 in Gazebo with hand gestures from a webcam, on a 2026 LTS stack.

```
usb_cam /image_raw -> hand_landmarker_node -> /hand/landmarks -> gesture_classifier_node -> /gesture -> gesture_to_cmd_vel_node -> /cmd_vel -> TurtleBot3 in Gazebo Harmonic
```

## 1. Stack

| Layer | Choice | Reason |
|---|---|---|
| ROS | ROS 2 Jazzy Jalisco, an LTS supported to May 2029 | Runs natively on Ubuntu 24.04 and has TurtleBot3 2.3.x packages. The next LTS, Lyrical Luth, targets Ubuntu 26.04 and has no TurtleBot3 release yet; moving later is a base-image change, since the nodes are plain rclpy. |
| Simulator | Gazebo Harmonic via ros_gz | Paired with Jazzy; turtlebot3_gazebo 2.3.x targets it. |
| Robot | TurtleBot3 burger in turtlebot3_world | The lightest model. Its /cmd_vel on Jazzy is geometry_msgs/TwistStamped, and the control node has a use_stamped parameter to fall back to Twist. |
| Camera | usb_cam publishing /image_raw | Keeps perception off the robot hardware, so the whole pipeline can run from a rosbag on a headless machine. |
| Hand tracking | MediaPipe Tasks HandLandmarker in VIDEO mode, one hand | The current API; mp.solutions is deprecated. Model files are fetched by scripts/download_models.sh and are not committed. mediapipe 1.x ships x86_64 and aarch64 wheels, so perception runs on ARM boards too. |
| Recogniser | Pre-trained MediaPipe GestureRecognizer task | A full demo with no training, run over /image_raw. |
| Packaging | colcon with ament_python nodes, an ament_cmake message package, Python launch files and YAML parameters | A standard ROS 2 layout. |
| Dev environment | Docker built from the multi-arch ros:jazzy image, with compose services dev and demo and a devcontainer | The same Dockerfile serves arm64 and x86_64. Native install is written up in the README. |
| Checks | ruff, pytest, launch_testing, GitHub Actions | landmarks.py and velocity.py have no ROS imports, so plain pytest covers them. |

## 2. Machines

| | Dev box | Demo box |
|---|---|---|
| Hardware | aarch64 VM, 2 vCPU, 3 GB RAM, no GPU, no display, no webcam | laptop with a display and webcam |
| Used for | code, unit tests, CI | Gazebo GUI, live camera, demo recording |
| Compose service | dev | demo |

The whole pipeline runs on the dev box from a rosbag or from still images. Only the Gazebo GUI and
the live webcam need the demo box. Camera data moves to the dev box as rosbags recorded with
scripts/record_bag.sh.

## 3. Layout

```
.devcontainer/              VS Code devcontainer on the compose dev service
.github/workflows/ci.yml    lint, unit tests, colcon build and colcon test
docker/                     Dockerfile, docker-compose.yml, entrypoint.sh
src/gesture_msgs/           Gesture.msg with header, label and confidence
src/gesture_recognition/    hand_landmarker_node, gesture_classifier_node, landmarks.py, launch, config, models
src/gesture_control/        gesture_to_cmd_vel_node, velocity.py, gesture_map.yaml, sim/camera/bringup launch
scripts/                    download_models.sh, record_bag.sh
docs/                       plan.md, architecture.md
```

## 4. Topics

| Topic | Type | Notes |
|---|---|---|
| /image_raw | sensor_msgs/Image | 640x480 at 30 FPS |
| /hand/landmarks | std_msgs/Float32MultiArray | 63 floats: wrist-relative, scale-normalised, left hand mirrored |
| /hand/image_annotated | sensor_msgs/Image | debug overlay, published only when subscribed |
| /gesture | gesture_msgs/Gesture | majority vote over 7 frames with at least 5 agreeing, then a 0.8 confidence gate, otherwise "none" |
| /cmd_vel | geometry_msgs/TwistStamped | deadman 0.5 s, acceleration ramp, clamped to the burger limits of 0.22 m/s and 2.84 rad/s |

Gesture map in src/gesture_control/config/gesture_map.yaml:

| Gesture | Action | linear.x | angular.z |
|---|---|---|---|
| open_palm, fist | stop | 0 | 0 |
| pointing_up | forward | 0.15 | 0 |
| victory | turn left | 0 | 0.6 |
| thumb_up | turn right | 0 | -0.6 |
| thumb_down | reverse | -0.10 | 0 |

## 5. Work plan

### 5.1 Simulation baseline
- Done: the burger bridge config maps /cmd_vel as geometry_msgs/TwistStamped, so use_stamped defaults to true.
- ros2 launch gesture_control sim.launch.py on the demo box, then drive with turtlebot3_teleop.
- Done when the robot moves from teleop.

### 5.2 Camera and hand landmarks
- Done: image_sequence_node stands in for the camera; the landmarker runs on arm64 at about 10 ms per 640x480 frame.
- camera.launch.py on the demo box; record a two minute bag of varied gestures and copy it to the dev box.
- hand_landmarker_node overlay visible in rqt_image_view at 20 FPS or better on the demo box.
- Done when ros2 topic hz /hand/landmarks matches the camera rate.

### 5.3 End to end with the MediaPipe baseline
- Done: the recognition launch test, five still images to /gesture, and the cmd_vel launch test pass in CI.
- Done: confidence gates set to 0.6 at the classifier and 0.5 at the control node, from measured MediaPipe scores.
- bringup.launch.py on the demo box with the webcam; tune window, min_votes and speeds. Check that STOP lands within 0.5 s and that the robot stays still when the hand leaves the frame.

### 5.4 Polish and release
- Measure latency from the Gesture stamp to the cmd_vel stamp; optionally add twist_mux so keyboard teleop overrides gestures.
- Write the run instructions for both machines and the native install notes, then tag v1.0.0.

### Later
- A real TurtleBot3, with perception on the laptop sharing a ROS_DOMAIN_ID with the robot.
- Dynamic gestures such as swipes, with a small 1D CNN over landmark sequences.
- Move to Lyrical Luth once its TurtleBot3 packages are released.

## 6. Risks

| Risk | Handling |
|---|---|
| Twist vs TwistStamped mismatch on /cmd_vel | the use_stamped parameter; both types bridge to Gazebo through ros_gz. |
| Webcam or X11 inside Docker on the demo box | the demo compose service passes /dev/video0, DISPLAY and /tmp/.X11-unix; native install is the fallback. |
| pip pulling numpy 2 over the Ubuntu numpy and breaking cv_bridge | constraints.txt pins numpy below 2, after CI failed on this once. |
| Mirrored webcam flips handedness | the frame is mirrored before detection, and left-hand landmarks are mirrored in normalize_landmarks. |
| Gesture flicker making the robot jerk | majority vote, acceleration ramp and deadman timeout. |
| Dev box too weak for Gazebo | only headless gz sim -s on the dev box; GUI work on the demo box. |

## 7. Checks

- Dev box: docker compose -f docker/docker-compose.yml run --rm dev, then colcon build --symlink-install, source install/setup.bash, pytest and colcon test.
- Demo box: docker compose -f docker/docker-compose.yml run --rm demo, then ros2 launch gesture_control bringup.launch.py and drive through turtlebot3_world.
- CI on every push: lint, pure-python unit tests, build, and the unit and launch tests.
