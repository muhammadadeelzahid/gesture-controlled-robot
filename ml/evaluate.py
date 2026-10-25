"""Evaluate the exported .tflite with LiteRT on a CSV (the same runtime the ROS node uses).

Usage: python ml/evaluate.py ml/data/holdout.csv
"""

from __future__ import annotations

import argparse

import numpy as np
from ai_edge_litert.interpreter import Interpreter

from common import LABELS, MODELS_DIR
from train import load


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="+")
    ap.add_argument("--model", default=str(MODELS_DIR / "gesture_mlp.tflite"))
    args = ap.parse_args()

    x, y = load(args.csv)
    interp = Interpreter(model_path=args.model)
    interp.allocate_tensors()
    i_in = interp.get_input_details()[0]["index"]
    i_out = interp.get_output_details()[0]["index"]
    pred = []
    for row in x:
        interp.set_tensor(i_in, row.reshape(1, -1))
        interp.invoke()
        pred.append(int(np.argmax(interp.get_tensor(i_out)[0])))
    pred = np.asarray(pred)
    print(f"accuracy: {(pred == y).mean():.4f} on {len(y)} samples")
    for i, label in enumerate(LABELS):
        m = y == i
        if m.any():
            print(f"  {label:12s} {(pred[m] == i).mean():.3f} (n={m.sum()})")


if __name__ == "__main__":
    main()
