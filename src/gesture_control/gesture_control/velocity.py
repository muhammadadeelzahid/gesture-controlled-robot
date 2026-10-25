"""Velocity logic: gesture lookup, deadman timeout, ramping and clamping.

No ROS imports so it can be unit-tested with plain pytest.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class VelocityLimits:
    max_linear: float = 0.22
    max_angular: float = 2.84
    linear_accel: float = 0.5
    angular_accel: float = 3.0


@dataclass
class VelocityController:
    gestures: dict[str, tuple[float, float]]
    limits: VelocityLimits = field(default_factory=VelocityLimits)
    deadman_timeout_s: float = 0.5
    min_confidence: float = 0.8

    _target: tuple[float, float] = (0.0, 0.0)
    _current: tuple[float, float] = (0.0, 0.0)
    _last_gesture_time: float | None = None

    def on_gesture(self, label: str, confidence: float, now: float) -> None:
        """Update the target velocity from a recognised gesture."""
        if confidence < self.min_confidence or label not in self.gestures:
            return  # ignored; deadman will stop the robot if nothing valid arrives
        self._target = self.gestures[label]
        self._last_gesture_time = now

    def step(self, now: float, dt: float) -> tuple[float, float]:
        """Advance the ramp by dt seconds and return (linear.x, angular.z)."""
        if (
            self._last_gesture_time is None
            or now - self._last_gesture_time > self.deadman_timeout_s
        ):
            self._target = (0.0, 0.0)

        lin = _ramp(self._current[0], self._target[0], self.limits.linear_accel * dt)
        ang = _ramp(self._current[1], self._target[1], self.limits.angular_accel * dt)
        lin = _clamp(lin, self.limits.max_linear)
        ang = _clamp(ang, self.limits.max_angular)
        self._current = (lin, ang)
        return self._current

    @property
    def target(self) -> tuple[float, float]:
        return self._target


def _ramp(current: float, target: float, max_delta: float) -> float:
    delta = target - current
    if abs(delta) <= max_delta:
        return target
    return current + max_delta * (1 if delta > 0 else -1)


def _clamp(value: float, limit: float) -> float:
    return max(-limit, min(limit, value))
