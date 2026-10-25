#!/usr/bin/env bash
# Download the MediaPipe Tasks models used by gesture_recognition.
set -euo pipefail
DEST="$(cd "$(dirname "$0")/.." && pwd)/src/gesture_recognition/models"
mkdir -p "$DEST"
BASE=https://storage.googleapis.com/mediapipe-models
curl -fsSL -o "$DEST/hand_landmarker.task" \
  "$BASE/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
curl -fsSL -o "$DEST/gesture_recognizer.task" \
  "$BASE/gesture_recognizer/gesture_recognizer/float16/latest/gesture_recognizer.task"
ls -lh "$DEST"
