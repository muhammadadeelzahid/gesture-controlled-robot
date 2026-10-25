"""ROS 2 node: MediaPipe GestureRecognizer over /image_raw -> /gesture."""

from __future__ import annotations

import os

import rclpy
from ament_index_python.packages import get_package_share_directory
from rclpy.node import Node

from gesture_msgs.msg import Gesture
from gesture_recognition.landmarks import MEDIAPIPE_LABELS, MajorityVote


class GestureClassifierNode(Node):
    def __init__(self) -> None:
        super().__init__("gesture_classifier_node")
        self.declare_parameter("model_path", "")
        self.declare_parameter("window", 7)
        self.declare_parameter("min_votes", 5)
        self.declare_parameter("min_confidence", 0.8)
        self.declare_parameter("mirror", True)

        self.min_confidence = self.get_parameter("min_confidence").value
        self.vote = MajorityVote(
            self.get_parameter("window").value, self.get_parameter("min_votes").value
        )
        self.pub = self.create_publisher(Gesture, "gesture", 10)
        share = get_package_share_directory("gesture_recognition")
        self._init_mediapipe(share)
        self.get_logger().info("gesture_classifier_node ready (MediaPipe GestureRecognizer)")

    def _init_mediapipe(self, share: str) -> None:
        import cv2
        import mediapipe as mp
        from cv_bridge import CvBridge
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision
        from sensor_msgs.msg import Image

        self._cv2, self._mp, self.bridge = cv2, mp, CvBridge()
        self.mirror = self.get_parameter("mirror").value
        model_path = self.get_parameter("model_path").value or os.path.join(
            share, "models", "gesture_recognizer.task"
        )
        options = vision.GestureRecognizerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=model_path),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=1,
        )
        self.recognizer_task = vision.GestureRecognizer.create_from_options(options)
        self.create_subscription(Image, "image_raw", self._on_image, 1)

    def _on_image(self, msg) -> None:
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        if self.mirror:
            frame = self._cv2.flip(frame, 1)
        rgb = self._cv2.cvtColor(frame, self._cv2.COLOR_BGR2RGB)
        mp_image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        ts_ms = int(msg.header.stamp.sec * 1000 + msg.header.stamp.nanosec / 1e6)
        result = self.recognizer_task.recognize_for_video(mp_image, ts_ms)
        if result.gestures and result.gestures[0]:
            cat = result.gestures[0][0]
            self._emit(MEDIAPIPE_LABELS.get(cat.category_name, "none"), float(cat.score))
        else:
            self._emit("none", 0.0)

    def _emit(self, raw_label: str, confidence: float) -> None:
        label = raw_label if confidence >= self.min_confidence else "none"
        smoothed = self.vote.push(label)
        out = Gesture()
        out.header.stamp = self.get_clock().now().to_msg()
        out.label = smoothed
        out.confidence = confidence if smoothed == raw_label else 0.0
        self.pub.publish(out)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = GestureClassifierNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
