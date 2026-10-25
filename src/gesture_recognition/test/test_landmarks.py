import numpy as np
import pytest

from gesture_recognition.landmarks import FEATURE_DIM, MajorityVote, normalize_landmarks


def hand(offset=(0.0, 0.0, 0.0), scale=1.0):
    rng = np.random.default_rng(0)
    pts = rng.uniform(-1, 1, size=(21, 3))
    pts[0] = 0.0
    return pts * scale + np.asarray(offset)


def test_shape_and_range():
    v = normalize_landmarks(hand())
    assert v.shape == (FEATURE_DIM,)
    assert np.abs(v).max() == pytest.approx(1.0)
    assert np.all(v[:3] == 0.0)  # wrist at origin


def test_translation_and_scale_invariant():
    a = normalize_landmarks(hand())
    b = normalize_landmarks(hand(offset=(0.3, -0.2, 0.1), scale=2.5))
    assert np.allclose(a, b, atol=1e-6)


def test_left_hand_mirrored_to_right():
    base = hand()
    left = base.copy()
    left[:, 0] *= -1
    assert np.allclose(normalize_landmarks(base, "Right"), normalize_landmarks(left, "Left"))


def test_majority_vote():
    mv = MajorityVote(window=5, min_votes=3)
    assert mv.push("fist") == "none"
    assert mv.push("fist") == "none"
    assert mv.push("fist") == "fist"
    assert mv.push("open_palm") == "fist"
    assert mv.push("open_palm") == "fist"
    assert mv.push("open_palm") == "open_palm"


def test_majority_vote_bad_config():
    with pytest.raises(ValueError):
        MajorityVote(window=3, min_votes=4)
