# Architecture

```
+----------+  /image_raw   +----------------------+ /hand/landmarks +--------------------------+ /gesture +------------------------+ /cmd_vel +--------------+
| usb_cam  +-------------->| hand_landmarker_node +---------------->| gesture_classifier_node  +--------->| gesture_to_cmd_vel_node+--------->| TurtleBot3   |
| webcam   |               | MediaPipe HandLandm. |                 | MediaPipe Gesture task   |          | deadman · ramp · clamp |          | Gazebo sim   |
+----------+               +----------+-----------+                 +--------------------------+          +------------------------+          +--------------+
                                      | /hand/image_annotated debug overlay, published only when subscribed
```

| Topic | Type | Notes |
|---|---|---|
| `/image_raw` | `sensor_msgs/Image` | 640×480 @30 FPS from `usb_cam`; replayable from a rosbag on a headless machine |
| `/hand/landmarks` | `std_msgs/Float32MultiArray` | 63 floats: wrist-relative, scale-normalised, left hands mirrored |
| `/hand/image_annotated` | `sensor_msgs/Image` | skeleton overlay for `rqt_image_view` |
| `/gesture` | `gesture_msgs/Gesture` | the label after a majority vote over 7 frames with at least 5 agreeing, then a confidence gate |
| `/cmd_vel` | `geometry_msgs/TwistStamped` | the Jazzy TurtleBot3 default; set `use_stamped:=false` for plain `Twist` |

`gesture_msgs` is an ament_cmake package, while `gesture_recognition` and `gesture_control` are
ament_python. `landmarks.py` and `velocity.py` have no ROS imports, so plain pytest covers them.
