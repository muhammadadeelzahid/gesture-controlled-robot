"""Shared helpers for the training scripts (mirrors gesture_recognition.landmarks)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "gesture_recognition"))

from gesture_recognition.landmarks import FEATURE_DIM, normalize_landmarks  # noqa: E402

LABELS = ["open_palm", "fist", "pointing_up", "victory", "thumb_up", "thumb_down"]
DATA_DIR = ROOT / "ml" / "data"
MODELS_DIR = ROOT / "src" / "gesture_recognition" / "models"

__all__ = ["FEATURE_DIM", "normalize_landmarks", "LABELS", "DATA_DIR", "MODELS_DIR", "ROOT"]
