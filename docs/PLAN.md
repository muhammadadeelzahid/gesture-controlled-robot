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
| Hand tracking | MediaPipe Tasks HandLandmarker (mediapipe 0.10.x, Python 3.12), VIDEO mode, one hand | Current API; mp.solutions is deprecated. Model files are fetched by scripts/download_models.sh and not committed. mediapipe only ships x86_64 Linux wheels. |
| Baseline recogniser | MediaPipe GestureRecognizer task (pre-trained) | Full demo with no training. recognizer:=mediapipe |
| Custom classifier | Keras 3 MLP on normalised 21x3 landmarks, exported to .tflite, run with LiteRT (ai-edge-litert) | Trains in minutes on CPU; the runtime image has no TensorFlow. recognizer:=custom |
| Packaging | colcon, ament_python nodes, ament_cmake message package, Python launch files, YAML parameters | Standard ROS 2 layout. |
| Dev environment | Docker from the multi-arch ros:jazzy image, compose services dev and demo, devcontainer | Same Dockerfile on arm64 and x86_64. Native install is documented in the README. |
| Checks | ruff, pytest, launch_testing, GitHub Actions | landmarks.py and velocity.py have no ROS imports and are tested with plain pytest. |

## 2. Machines

| | Dev box (VM) | Demo box (laptop) |
|---|---|---|
| Hardware | aarch64, 2 vCPU, 3 GB RAM, no GPU, no display, no webcam | x86_64, display, webcam |
| Used for | code, unit tests, training on landmark CSVs, headless Gazebo smoke test, CI | Gazebo GUI, live camera, data collection, demo recording |
| Compose service | dev | demo |

mediapipe does not install on the dev box (no aarch64 wheel), so the landmarker and the mediapipe recognizer only run on the demo box. Camera data moves to the dev box as rosbags (scripts/record_bag.sh).

## 3. Layout

```
.devcontainer/              VS Code devcontainer on the compose dev service
.github/workflows/ci.yml    lint, colcon build, pytest, colcon test, headless Gazebo smoke test
docker/                     Dockerfile, docker-compose.yml, entrypoint.sh
src/gesture_msgs/           Gesture.msg (header, label, confidence)
src/gesture_recognition/    hand_landmarker_node, gesture_classifier_node, landmarks.py, launch, config, models/
src/gesture_control/        gesture_to_cmd_vel_node, velocity.py, gesture_map.yaml, sim/camera/bringup launch
ml/                         collect_data.py, train.py, evaluate.py, requirements-train.txt, data/
scripts/                    download_models.sh, record_bag.sh, headless_smoke_test.sh
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
- Done: scripts/headless_smoke_test.sh passes on the dev box (robot moves about 2 m in 10 s at 0.2 m/s).
- ros2 launch gesture_control sim.launch.py on the demo box, then drive with turtlebot3_teleop.
- Done when: robot moves from teleop and the smoke test is green in CI.

### 5.2 Camera and hand landmarks
- camera.launch.py on the demo box; record a two minute bag of varied gestures and copy it to the dev box.
- hand_landmarker_node overlay visible in rqt_image_view at 20 FPS or better on the demo box.
- Done when: ros2 topic hz /hand/landmarks matches the camera rate.

### 5.3 End to end with the MediaPipe baseline (first demo)
- bringup.launch.py recognizer:=mediapipe on the demo box.
- Tune window, min_votes, min_confidence and speeds. Check that STOP lands within 0.5 s and that the robot does not move when the hand leaves the frame.
- launch_testing for the cmd_vel node passes in CI.

### 5.4 Custom Keras 3 classifier
- ml/collect_data.py: about 300 samples per class, two or more people, both hands, varied lighting and distance.
- ml/train.py on the dev box writes gesture_mlp.tflite, labels.txt and a confusion matrix. Target 95 % validation accuracy or better, no confusion pair above 3 %.
- ml/evaluate.py on a held-out CSV through LiteRT, the same runtime the node uses.
- bringup.launch.py recognizer:=custom passes the same drive test as 5.3.

### 5.5 Polish and release
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
| Dev box too weak for Gazebo | only headless gz sim -s for the smoke test; GUI work on the demo box. |

## 7. Checks

- Dev box: docker compose -f docker/docker-compose.yml run --rm dev, then colcon build --symlink-install, source install/setup.bash, pytest, colcon test, scripts/headless_smoke_test.sh.
- Demo box: docker compose -f docker/docker-compose.yml run --rm demo, then ros2 launch gesture_control bringup.launch.py recognizer:=mediapipe (later custom) and drive through turtlebot3_world.
- CI on every push: lint, build, unit and launch tests, headless smoke test.
