"""ROS 2 node: publish still images on /image_raw, one after another.

Stands in for the camera on machines without one, and feeds the launch tests.
"""

from __future__ import annotations

import os
from pathlib import Path

import cv2
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp"}


class ImageSequenceNode(Node):
    def __init__(self) -> None:
        super().__init__("image_sequence_node")
        self.declare_parameter("images", "")  # comma separated files and/or directories
        self.declare_parameter("rate_hz", 15.0)
        self.declare_parameter("hold_s", 3.0)
        self.declare_parameter("loop", True)
        self.declare_parameter("width", 640)

        paths = [p.strip() for p in self.get_parameter("images").value.split(",") if p.strip()]
        self.files = sorted(self._expand(paths))
        if not self.files:
            raise RuntimeError(f"no images found in {paths}")
        width = self.get_parameter("width").value
        self.frames = []
        for f in self.files:
            img = cv2.imread(f)
            if img is None:
                self.get_logger().warning(f"could not read {f}")
                continue
            if width and img.shape[1] != width:
                h = int(img.shape[0] * width / img.shape[1])
                img = cv2.resize(img, (width, h))
            self.frames.append((Path(f).stem, img))

        self.bridge = CvBridge()
        self.pub = self.create_publisher(Image, "image_raw", 1)
        self.pub_name = self.create_publisher(String, "image_sequence/name", 1)
        self.rate = self.get_parameter("rate_hz").value
        self.per_image = max(1, int(self.get_parameter("hold_s").value * self.rate))
        self.loop = self.get_parameter("loop").value
        self.tick = 0
        self.timer = self.create_timer(1.0 / self.rate, self._on_timer)
        self.get_logger().info(f"{len(self.frames)} images, {self.per_image} frames each")

    @staticmethod
    def _expand(paths: list[str]) -> list[str]:
        out: list[str] = []
        for p in paths:
            if os.path.isdir(p):
                out += [str(f) for f in Path(p).iterdir() if f.suffix.lower() in IMAGE_SUFFIXES]
            else:
                out.append(p)
        return out

    def _on_timer(self) -> None:
        idx = self.tick // self.per_image
        if idx >= len(self.frames):
            if not self.loop:
                self.timer.cancel()
                return
            self.tick = 0
            idx = 0
        name, img = self.frames[idx]
        msg = self.bridge.cv2_to_imgmsg(img, encoding="bgr8")
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "camera"
        self.pub.publish(msg)
        self.pub_name.publish(String(data=name))
        self.tick += 1


def main(args=None) -> None:
    rclpy.init(args=args)
    node = ImageSequenceNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
