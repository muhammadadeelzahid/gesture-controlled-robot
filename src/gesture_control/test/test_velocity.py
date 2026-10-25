from gesture_control.velocity import VelocityController, VelocityLimits

GESTURES = {"open_palm": (0.0, 0.0), "pointing_up": (0.15, 0.0), "victory": (0.0, 0.6)}


def make(**kw):
    return VelocityController(gestures=GESTURES, limits=VelocityLimits(linear_accel=1.0), **kw)


def test_no_gesture_means_zero():
    c = make()
    assert c.step(now=0.0, dt=0.05) == (0.0, 0.0)


def test_gesture_maps_to_velocity_after_ramp():
    c = make()
    c.on_gesture("pointing_up", 0.95, now=0.0)
    v = c.step(now=0.05, dt=0.05)
    assert 0.0 < v[0] <= 0.15  # ramping up
    for i in range(10):
        now = 0.1 + i * 0.05
        c.on_gesture("pointing_up", 0.95, now=now)  # keep the deadman alive
        v = c.step(now=now, dt=0.05)
    assert v == (0.15, 0.0)


def test_low_confidence_ignored():
    c = make()
    c.on_gesture("pointing_up", 0.5, now=0.0)
    assert c.target == (0.0, 0.0)


def test_unknown_label_ignored():
    c = make()
    c.on_gesture("wave", 0.99, now=0.0)
    assert c.target == (0.0, 0.0)


def test_deadman_stops_robot():
    c = make(deadman_timeout_s=0.5)
    c.on_gesture("victory", 0.99, now=0.0)
    for i in range(10):
        c.step(now=i * 0.05, dt=0.05)
    assert c.step(now=0.45, dt=0.05)[1] > 0.0
    for i in range(20):
        v = c.step(now=1.0 + i * 0.05, dt=0.05)
    assert v == (0.0, 0.0)


def test_clamped_to_limits():
    c = VelocityController(
        gestures={"fast": (5.0, 10.0)},
        limits=VelocityLimits(
            max_linear=0.22, max_angular=2.84, linear_accel=100, angular_accel=100
        ),
    )
    c.on_gesture("fast", 1.0, now=0.0)
    assert c.step(now=0.0, dt=0.05) == (0.22, 2.84)
