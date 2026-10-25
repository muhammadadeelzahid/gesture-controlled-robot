"""Render a recorded demo bag into docs/demo: trajectory, timeline and a GIF.

Usage: python3 scripts/plot_demo.py bags/demo docs/demo
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import cv2
import matplotlib
import numpy as np
from PIL import Image as PILImage
from rclpy.serialization import deserialize_message
from rosbag2_py import ConverterOptions, SequentialReader, StorageOptions
from rosidl_runtime_py.utilities import get_message

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

COLORS = {
    "open_palm": "#777777",
    "fist": "#333333",
    "pointing_up": "#1f77b4",
    "victory": "#2ca02c",
    "thumb_up": "#ff7f0e",
    "thumb_down": "#d62728",
    "none": "#cccccc",
}


def read_bag(path: str) -> dict[str, list[tuple[float, object]]]:
    reader = SequentialReader()
    reader.open(StorageOptions(uri=path, storage_id="mcap"), ConverterOptions("", ""))
    types = {t.name: get_message(t.type) for t in reader.get_all_topics_and_types()}
    out: dict[str, list[tuple[float, object]]] = {name: [] for name in types}
    while reader.has_next():
        topic, data, t_ns = reader.read_next()
        out[topic].append((t_ns * 1e-9, deserialize_message(data, types[topic])))
    return out


def yaw_from(q) -> float:
    return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))


def label_at(gestures: list[tuple[float, object]], t: float) -> str:
    label = "none"
    for ts, msg in gestures:
        if ts > t:
            break
        label = msg.label
    return label


def plot_trajectory(bag, out: Path) -> None:
    odom = bag.get("/odom", [])
    gestures = bag.get("/gesture", [])
    if not odom:
        return
    fig, ax = plt.subplots(figsize=(7, 4.5))
    xs = [m.pose.pose.position.x for _, m in odom]
    ys = [m.pose.pose.position.y for _, m in odom]
    for i in range(1, len(odom)):
        lab = label_at(gestures, odom[i][0])
        ax.plot(xs[i - 1 : i + 1], ys[i - 1 : i + 1], color=COLORS.get(lab, "k"), lw=2)
    step = max(1, len(odom) // 12)
    for _, m in odom[::step]:
        yaw = yaw_from(m.pose.pose.orientation)
        ax.arrow(
            m.pose.pose.position.x,
            m.pose.pose.position.y,
            0.04 * math.cos(yaw),
            0.04 * math.sin(yaw),
            head_width=0.02,
            color="k",
        )
    ax.plot(xs[0], ys[0], "ko", label="start")
    for lab, col in COLORS.items():
        if any(m.label == lab for _, m in gestures):
            ax.plot([], [], color=col, lw=3, label=lab)
    ax.set_aspect("equal", adjustable="datalim")
    ax.margins(0.15)
    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")
    ax.set_title("robot path in the odom frame, coloured by gesture")
    ax.legend(loc="best", fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / "trajectory.png", dpi=120)


def plot_timeline(bag, out: Path) -> None:
    gestures = bag.get("/gesture", [])
    cmds = bag.get("/cmd_vel", [])
    if not gestures or not cmds:
        return
    t0 = min(gestures[0][0], cmds[0][0])
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 5), sharex=True)
    labels = sorted({m.label for _, m in gestures})
    a1.scatter(
        [t - t0 for t, _ in gestures],
        [labels.index(m.label) for _, m in gestures],
        c=[COLORS.get(m.label, "k") for _, m in gestures],
        s=8,
    )
    a1.set_yticks(range(len(labels)), labels)
    a1.set_title("/gesture")
    tc = [t - t0 for t, _ in cmds]
    a2.plot(tc, [m.twist.linear.x for _, m in cmds], label="linear.x [m/s]")
    a2.plot(tc, [m.twist.angular.z for _, m in cmds], label="angular.z [rad/s]")
    a2.set_title("/cmd_vel")
    a2.set_xlabel("time [s]")
    a2.legend(loc="upper right", fontsize=8)
    a2.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / "timeline.png", dpi=120)


def make_gif(bag, out: Path, width: int = 320, fps: int = 4) -> None:
    frames = bag.get("/hand/image_annotated", [])
    gestures = bag.get("/gesture", [])
    cmds = bag.get("/cmd_vel", [])
    if not frames:
        return
    images = []
    last = -1.0
    for t, msg in frames:
        if t - last < 1.0 / fps:
            continue
        last = t
        bgr = np.frombuffer(msg.data, np.uint8).reshape(msg.height, msg.width, -1)
        h = int(bgr.shape[0] * width / bgr.shape[1])
        bgr = cv2.resize(bgr, (width, h))
        lab = label_at(gestures, t)
        cmd = next((m for ts, m in reversed(cmds) if ts <= t), None)
        text = (
            lab
            if cmd is None
            else f"{lab}  v={cmd.twist.linear.x:+.2f} w={cmd.twist.angular.z:+.2f}"
        )
        cv2.rectangle(bgr, (0, 0), (width, 22), (0, 0, 0), -1)
        cv2.putText(bgr, text, (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
        images.append(PILImage.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)))
    if images:
        images[0].save(
            out / "demo.gif",
            save_all=True,
            append_images=images[1:],
            duration=int(1000 / fps),
            loop=0,
        )


def main() -> None:
    bag_path, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    bag = read_bag(bag_path)
    for topic, msgs in bag.items():
        print(f"{topic}: {len(msgs)} messages")
    plot_trajectory(bag, out)
    plot_timeline(bag, out)
    make_gif(bag, out)
    print("wrote", sorted(p.name for p in out.iterdir()))


if __name__ == "__main__":
    main()
