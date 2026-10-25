"""Collect labelled, normalised hand landmarks into a CSV.

Webcam:  python ml/collect_data.py --out ml/data/session1.csv
  Keys 0-5 record the current frame with that label (hold to burst), q quits.
  0 open_palm  1 fist  2 pointing_up  3 victory  4 thumb_up  5 thumb_down

Images:  python ml/collect_data.py --out ml/data/images.csv --images DIR [--augment N]
  DIR holds one sub-directory per label (open_palm/, fist/, ...) with images in it.
  --augment N also runs N randomly rotated, scaled, shifted and re-lit copies of each image.
  Each image is fed to the landmarker in VIDEO mode for --hold-frames frames, like the
  nodes do, because tracking settles on slightly different landmarks than a one-shot detect.
"""

from __future__ import annotations

import argparse
import csv
import time

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from common import LABELS, MODELS_DIR, normalize_landmarks


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--camera", type=int, default=0)
    ap.add_argument("--images", help="directory with one sub-directory per label")
    ap.add_argument("--augment", type=int, default=0, help="extra random variants per image")
    ap.add_argument("--hold-frames", type=int, default=6, help="video-mode frames per image")
    ap.add_argument("--model", default=str(MODELS_DIR / "hand_landmarker.task"))
    args = ap.parse_args()

    if args.images:
        from_images(args)
        return

    options = vision.HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=args.model),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=1,
    )
    landmarker = vision.HandLandmarker.create_from_options(options)
    cap = cv2.VideoCapture(args.camera)
    counts = {label: 0 for label in LABELS}
    t0 = time.time()

    with open(args.out, "a", newline="") as f:
        writer = csv.writer(f)
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = landmarker.detect_for_video(
                mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), int((time.time() - t0) * 1000)
            )
            feat = None
            if result.hand_landmarks:
                handed = result.handedness[0][0].category_name if result.handedness else "Right"
                pts = np.array(
                    [[p.x, p.y, p.z] for p in result.hand_landmarks[0]], dtype=np.float32
                )
                feat = normalize_landmarks(pts, handed)
                h, w = frame.shape[:2]
                for p in pts:
                    cv2.circle(frame, (int(p[0] * w), int(p[1] * h)), 3, (0, 255, 0), -1)

            y = 20
            for i, label in enumerate(LABELS):
                cv2.putText(
                    frame,
                    f"{i}:{label} {counts[label]}",
                    (10, y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    1,
                )
                y += 20
            cv2.imshow("collect (q to quit)", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if feat is not None and ord("0") <= key <= ord("5"):
                label = LABELS[key - ord("0")]
                writer.writerow([label, *feat.tolist()])
                counts[label] += 1

    cap.release()
    cv2.destroyAllWindows()
    print(counts)


def random_variant(bgr: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Rotate, scale, shift and re-light an image; a cheap stand-in for more photos."""
    h, w = bgr.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), rng.uniform(-25, 25), rng.uniform(0.8, 1.2))
    m[:, 2] += rng.uniform(-0.08, 0.08, size=2) * (w, h)
    out = cv2.warpAffine(bgr, m, (w, h), borderMode=cv2.BORDER_REFLECT)
    out = cv2.convertScaleAbs(out, alpha=rng.uniform(0.7, 1.3), beta=rng.uniform(-30, 30))
    if rng.random() < 0.5:
        out = cv2.flip(out, 1)
    return out


def from_images(args) -> None:
    """Run the landmarker on each image (and its variants); the label is the directory name."""
    from pathlib import Path

    options = vision.HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=args.model),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=1,
    )
    landmarker = vision.HandLandmarker.create_from_options(options)
    rng = np.random.default_rng(0)
    ts_ms = 0
    counts = {label: 0 for label in LABELS}
    with open(args.out, "a", newline="") as f:
        writer = csv.writer(f)
        for path in sorted(Path(args.images).rglob("*")):
            label = path.parent.name
            if label not in LABELS or path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                continue
            bgr = cv2.imread(str(path))
            if bgr is None:
                continue
            variants = [bgr] + [random_variant(bgr, rng) for _ in range(args.augment)]
            for i, img in enumerate(variants):
                rgb = cv2.cvtColor(cv2.flip(img, 1), cv2.COLOR_BGR2RGB)
                mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                found = False
                for _ in range(max(1, args.hold_frames)):
                    ts_ms += 100
                    result = landmarker.detect_for_video(mp_img, ts_ms)
                    if not result.hand_landmarks:
                        continue
                    found = True
                    handed = result.handedness[0][0].category_name if result.handedness else "Right"
                    pts = np.array(
                        [[p.x, p.y, p.z] for p in result.hand_landmarks[0]], dtype=np.float32
                    )
                    writer.writerow([label, *normalize_landmarks(pts, handed).tolist()])
                    counts[label] += 1
                if i == 0 and not found:
                    print(f"no hand in {path}")
    print(counts)


if __name__ == "__main__":
    main()
