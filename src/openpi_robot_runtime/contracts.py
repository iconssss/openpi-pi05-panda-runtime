"""Explicit contracts at the policy / robot boundary.

These types deliberately represent the post-OpenPI output contract used by the
DROID example: seven joint-velocity values and one gripper-position value.
They are not a claim about every OpenPI embodiment or robot SDK.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Sequence


DROID_LIKE_ACTION_DIM = 8


@dataclass(frozen=True)
class Observation:
    """Minimal robot-side observation for the mock closed loop."""

    joint_position: tuple[float, ...]
    gripper_position: float
    prompt: str
    step_index: int


@dataclass(frozen=True)
class ActionChunk:
    """A policy prediction with shape ``(prediction_horizon, action_dim)``."""

    actions: tuple[tuple[float, ...], ...]

    @property
    def horizon(self) -> int:
        return len(self.actions)

    @property
    def action_dim(self) -> int:
        return len(self.actions[0]) if self.actions else 0

    @classmethod
    def from_rows(cls, rows: Sequence[Sequence[float]]) -> "ActionChunk":
        return cls(actions=tuple(tuple(float(value) for value in row) for row in rows))

    def validate(self, *, expected_action_dim: int = DROID_LIKE_ACTION_DIM) -> None:
        if not self.actions:
            raise ValueError("Policy returned an empty action chunk.")
        if self.action_dim != expected_action_dim:
            raise ValueError(
                f"Expected action_dim={expected_action_dim}, got {self.action_dim}. "
                "Check the selected policy embodiment and output transform."
            )
        for row_index, row in enumerate(self.actions):
            if len(row) != self.action_dim:
                raise ValueError(f"Action row {row_index} has inconsistent dimensionality.")
            if not all(isfinite(value) for value in row):
                raise ValueError(f"Action row {row_index} contains NaN or Inf.")


@dataclass(frozen=True)
class PolicyResponse:
    """Policy result plus optional timing reported by the policy server."""

    action_chunk: ActionChunk
    policy_infer_ms: float | None = None
    server_infer_ms: float | None = None

