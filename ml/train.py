"""Train a Keras 3 MLP on normalised landmarks and export .tflite + labels.txt.

Usage: python ml/train.py ml/data/*.csv [--epochs 100] [--out src/gesture_recognition/models]
"""

from __future__ import annotations

import argparse
import glob
from pathlib import Path

import numpy as np

from common import FEATURE_DIM, LABELS, MODELS_DIR


def load(paths: list[str]) -> tuple[np.ndarray, np.ndarray]:
    xs, ys = [], []
    for path in paths:
        for row in np.loadtxt(path, delimiter=",", dtype=str, ndmin=2):
            if row[0] not in LABELS:
                continue
            ys.append(LABELS.index(row[0]))
            xs.append(row[1:].astype(np.float32))
    x = np.stack(xs)
    assert x.shape[1] == FEATURE_DIM, x.shape
    return x, np.asarray(ys)


def augment(x: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Random in-plane rotation, scale and jitter on the (21,3) landmarks."""
    pts = x.reshape(-1, 21, 3).copy()
    theta = rng.uniform(-0.3, 0.3, size=(len(pts), 1))
    c, s = np.cos(theta), np.sin(theta)
    xy = pts[:, :, :2]
    pts[:, :, 0] = c * xy[:, :, 0] - s * xy[:, :, 1]
    pts[:, :, 1] = s * xy[:, :, 0] + c * xy[:, :, 1]
    pts *= rng.uniform(0.85, 1.15, size=(len(pts), 1, 1))
    pts += rng.normal(0, 0.02, size=pts.shape)
    return pts.reshape(len(pts), -1).astype(np.float32)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="+")
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--out", default=str(MODELS_DIR))
    args = ap.parse_args()

    import keras
    import tensorflow as tf
    from sklearn.metrics import confusion_matrix
    from sklearn.model_selection import train_test_split

    paths = [p for pat in args.csv for p in glob.glob(pat)]
    x, y = load(paths)
    x_tr, x_va, y_tr, y_va = train_test_split(x, y, test_size=0.2, stratify=y, random_state=0)
    rng = np.random.default_rng(0)
    x_tr = np.concatenate([x_tr, augment(x_tr, rng), augment(x_tr, rng)])
    y_tr = np.concatenate([y_tr, y_tr, y_tr])

    model = keras.Sequential(
        [
            keras.Input(shape=(FEATURE_DIM,)),
            keras.layers.Dense(128, activation="relu"),
            keras.layers.Dropout(0.3),
            keras.layers.Dense(64, activation="relu"),
            keras.layers.Dropout(0.2),
            keras.layers.Dense(len(LABELS), activation="softmax"),
        ]
    )
    model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    early_stop = keras.callbacks.EarlyStopping(patience=10, restore_best_weights=True)
    model.fit(
        x_tr,
        y_tr,
        validation_data=(x_va, y_va),
        epochs=args.epochs,
        batch_size=64,
        callbacks=[early_stop],
        verbose=2,
    )
    _, acc = model.evaluate(x_va, y_va, verbose=0)
    print(f"validation accuracy: {acc:.4f}")
    print(confusion_matrix(y_va, model.predict(x_va, verbose=0).argmax(1)))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    model.save(out / "gesture_mlp.keras")
    tflite = tf.lite.TFLiteConverter.from_keras_model(model).convert()
    (out / "gesture_mlp.tflite").write_bytes(tflite)
    (out / "labels.txt").write_text("\n".join(LABELS) + "\n")
    print(f"wrote {out / 'gesture_mlp.tflite'} ({len(tflite)} bytes)")


if __name__ == "__main__":
    main()
