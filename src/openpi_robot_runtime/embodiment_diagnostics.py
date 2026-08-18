"""Pre-registered, task-independent measures for embodiment-mismatch studies.

These utilities deliberately do not search joint permutations or tune a mapping
on evaluation outcomes.  They make the fixed diagnostic conditions used in
Stage 17 explicit and unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt


@dataclass(frozen=True)
class ActionInterpretation:
    """A fixed diagnostic interpretation of the seven arm action entries."""

    name: str
    arm_sign: float = 1.0
    arm_gain: float = 1.0

    def __post_init__(self) -> None:
        if not self.name or self.arm_sign not in (-1.0, 1.0) or self.arm_gain <= 0:
            raise ValueError("Action interpretation needs a name, sign +/-1, and positive gain.")

    def apply(self, action: tuple[float, ...]) -> tuple[float, ...]:
        if len(action) != 8 or not all(isfinite(value) for value in action):
            raise ValueError("Expected one finite 8-D DROID-like action.")
        return tuple(self.arm_sign * self.arm_gain * value for value in action[:7]) + (action[7],)


def cosine_alignment(left: tuple[float, ...], right: tuple[float, ...]) -> float | None:
    """Return direction alignment, or ``None`` when either vector is zero."""
    if len(left) != len(right) or not left or not all(isfinite(v) for v in (*left, *right)):
        raise ValueError("Alignment needs equally-sized finite, non-empty vectors.")
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return None
    return sum(a * b for a, b in zip(left, right, strict=True)) / (left_norm * right_norm)


def one_step_progress(initial_distance_m: float, final_distance_m: float) -> float:
    """Positive values mean that an action reduced task distance."""
    if not all(isfinite(value) and value >= 0.0 for value in (initial_distance_m, final_distance_m)):
        raise ValueError("Distances must be finite and non-negative.")
    return initial_distance_m - final_distance_m
