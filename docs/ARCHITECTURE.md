# Architecture

```
+----------+  /image_raw   +----------------------+ /hand/landmarks +--------------------------+ /gesture +------------------------+ /cmd_vel +--------------+
| usb_cam  +-------------->| hand_landmarker_node +---------------->| gesture_classifier_node  +--------->| gesture_to_cmd_vel_node+--------->| TurtleBot3   |
| (webcam) |               | MediaPipe HandLandm. |                 | MediaPipe Gesture task   |          | deadman · ramp · clamp |          | Gazebo (gz)  |
+----------+               +----------+-----------+                 +--------------------------+          +------------------------+          +--------------+
                                      | /hand/image_annotated (debug, only when subscribed)
```

| Topic | Type | Notes |
|---|---|---|
| `/image_raw` | `sensor_msgs/Image` | 640×480 @30 FPS from `usb_cam`; replayable from a rosbag on a headless machine |
| `/hand/landmarks` | `std_msgs/Float32MultiArray` | 63 floats: wrist-relative, scale-normalised, left hands mirrored |
| `/hand/image_annotated` | `sensor_msgs/Image` | skeleton overlay for `rqt_image_view` |
| `/gesture` | `gesture_msgs/Gesture` | label after majority vote (7 frames, ≥5 agree) and confidence gate |
| `/cmd_vel` | `geometry_msgs/TwistStamped` | Jazzy TurtleBot3 default; `use_stamped:=false` for plain `Twist` |

Packages: `gesture_msgs` (ament_cmake), `gesture_recognition` and `gesture_control` (ament_python).
`landmarks.py` and `velocity.py` have no ROS imports and are covered by plain pytest.
