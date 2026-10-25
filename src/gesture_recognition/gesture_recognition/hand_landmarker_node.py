"""ROS 2 node: /image_raw -> /hand/landmarks (63 floats) and /hand/image_annotated."""

from __future__ import annotations

import os

import cv2
import numpy as np
import rclpy
from ament_index_python.packages import get_package_share_directory
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float32MultiArray

from gesture_recognition.landmarks import normalize_landmarks

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20), (0, 17),
]  # fmt: skip


class HandLandmarkerNode(Node):
    def __init__(self) -> None:
        super().__init__("hand_landmarker_node")
        self.declare_parameter("model_path", "")
        self.declare_parameter("mirror", True)
        self.declare_parameter("num_hands", 1)
        self.declare_parameter("min_detection_confidence", 0.5)
        self.declare_parameter("min_tracking_confidence", 0.5)
        self.declare_parameter("publish_annotated", True)

        model_path = self.get_parameter("model_path").value or os.path.join(
            get_package_share_directory("gesture_recognition"), "models", "hand_landmarker.task"
        )
        self.mirror = self.get_parameter("mirror").value
        self.publish_annotated = self.get_parameter("publish_annotated").value

        import mediapipe as mp  # imported late so --help etc. stay fast
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision

        self._mp = mp
        options = vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=model_path),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=self.get_parameter("num_hands").value,
            min_hand_detection_confidence=self.get_parameter("min_detection_confidence").value,
            min_tracking_confidence=self.get_parameter("min_tracking_confidence").value,
        )
        self.landmarker = vision.HandLandmarker.create_from_options(options)

        self.bridge = CvBridge()
        self.pub_landmarks = self.create_publisher(Float32MultiArray, "hand/landmarks", 10)
        self.pub_image = self.create_publisher(Image, "hand/image_annotated", 1)
        self.sub = self.create_subscription(Image, "image_raw", self._on_image, 1)
        self.get_logger().info(f"HandLandmarker loaded from {model_path}")

    def _on_image(self, msg: Image) -> None:
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        if self.mirror:
            frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        ts_ms = int(msg.header.stamp.sec * 1000 + msg.header.stamp.nanosec / 1e6)
        result = self.landmarker.detect_for_video(mp_image, ts_ms)

        if result.hand_landmarks:
            lm = result.hand_landmarks[0]
            handedness = result.handedness[0][0].category_name if result.handedness else "Right"
            pts = np.array([[p.x, p.y, p.z] for p in lm], dtype=np.float32)
            out = Float32MultiArray()
            out.data = normalize_landmarks(pts, handedness).tolist()
            self.pub_landmarks.publish(out)
            if self.publish_annotated and self.pub_image.get_subscription_count() > 0:
                self._draw(frame, pts)

        if self.publish_annotated and self.pub_image.get_subscription_count() > 0:
            img = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
            img.header = msg.header
            self.pub_image.publish(img)

    @staticmethod
    def _draw(frame: np.ndarray, pts: np.ndarray) -> None:
        h, w = frame.shape[:2]
        px = [(int(x * w), int(y * h)) for x, y, _ in pts]
        for a, b in HAND_CONNECTIONS:
            cv2.line(frame, px[a], px[b], (0, 255, 0), 2)
        for p in px:
            cv2.circle(frame, p, 4, (0, 0, 255), -1)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = HandLandmarkerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
