"""Landmark normalisation and temporal smoothing. No ROS imports."""

from __future__ import annotations

from collections import Counter, deque

import numpy as np

NUM_LANDMARKS = 21
FEATURE_DIM = NUM_LANDMARKS * 3

# MediaPipe GestureRecognizer canned category names -> this project's labels.
MEDIAPIPE_LABELS = {
    "Open_Palm": "open_palm",
    "Closed_Fist": "fist",
    "Pointing_Up": "pointing_up",
    "Victory": "victory",
    "Thumb_Up": "thumb_up",
    "Thumb_Down": "thumb_down",
    "ILoveYou": "i_love_you",
    "None": "none",
}


def normalize_landmarks(points: np.ndarray, handedness: str = "Right") -> np.ndarray:
    """Make a 21x3 landmark array translation/scale invariant and handedness-symmetric.

    - subtract the wrist (landmark 0)
    - mirror x for left hands so both hands share one feature space
    - divide by the largest absolute coordinate so values lie in [-1, 1]
    Returns a flat float32 vector of length 63.
    """
    pts = np.asarray(points, dtype=np.float32).reshape(NUM_LANDMARKS, 3).copy()
    pts -= pts[0]
    if handedness.lower().startswith("l"):
        pts[:, 0] *= -1.0
    scale = float(np.abs(pts).max())
    if scale > 0:
        pts /= scale
    return pts.reshape(-1)


class MajorityVote:
    """Emit a label only when at least `min_votes` of the last `window` frames agree."""

    def __init__(self, window: int = 7, min_votes: int = 5) -> None:
        if min_votes > window:
            raise ValueError("min_votes must be <= window")
        self.window = window
        self.min_votes = min_votes
        self._buf: deque[str] = deque(maxlen=window)

    def push(self, label: str) -> str:
        self._buf.append(label)
        label, count = Counter(self._buf).most_common(1)[0]
        return label if count >= self.min_votes else "none"

    def reset(self) -> None:
        self._buf.clear()
