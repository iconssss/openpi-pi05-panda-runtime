"""Explicit, limited DROID-like action bridge for a 7-DoF Panda simulator.

This module is intentionally independent of MuJoCo so its safety-relevant
mapping can be unit tested locally.  It does *not* claim that a DROID-trained
policy transfers to Panda: it only defines the simulator control convention
used for a controlled integration experiment.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .contracts import DROID_LIKE_ACTION_DIM


@dataclass(frozen=True)
class PandaPositionCommand:
    """Seven arm position targets plus a normalized gripper command."""

    joint_position_targets: tuple[float, ...]
    gripper_normalized: float
    clipped: bool


@dataclass(frozen=True)
class DroidLikePandaActionBridge:
    """Integrate limited DROID-like joint velocities into Panda targets.

    ``joint_limits`` must be in the same ordered seven-joint convention as the
    MuJoCo arm actuators resolved by the caller.  The policy's eighth value is
    limited to [0, 1]; conversion to a MuJoCo finger actuator range belongs in
    the simulator-specific caller because actuator control ranges vary by XML.
    """

    joint_limits: tuple[tuple[float, float], ...]
    control_dt_seconds: float = 1.0 / 15.0
    max_joint_velocity: float = 1.0

    def __post_init__(self) -> None:
        if len(self.joint_limits) != 7:
            raise ValueError("Panda bridge requires limits for exactly seven arm joints.")
        if self.control_dt_seconds <= 0 or self.max_joint_velocity <= 0:
            raise ValueError("Control dt and velocity limit must be positive.")
        if any(lower > upper for lower, upper in self.joint_limits):
            raise ValueError("Each Panda joint limit must be ordered lower <= upper.")

    def to_position_command(
        self,
        *,
        current_joint_positions: tuple[float, ...],
        droid_like_action: tuple[float, ...],
    ) -> PandaPositionCommand:
        if len(current_joint_positions) != 7 or len(droid_like_action) != DROID_LIKE_ACTION_DIM:
            raise ValueError("Expected seven joint positions and one 8-D DROID-like action.")
        if not all(isfinite(value) for value in (*current_joint_positions, *droid_like_action)):
            raise ValueError("Panda bridge rejects NaN or Inf action/state values.")

        clipped = False
        targets: list[float] = []
        for position, velocity, (lower, upper) in zip(
            current_joint_positions, droid_like_action[:7], self.joint_limits, strict=True
        ):
            limited_velocity = min(max(velocity, -self.max_joint_velocity), self.max_joint_velocity)
            raw_target = position + limited_velocity * self.control_dt_seconds
            target = min(max(raw_target, lower), upper)
            clipped = clipped or limited_velocity != velocity or target != raw_target
            targets.append(target)
        raw_gripper = droid_like_action[7]
        gripper = min(max(raw_gripper, 0.0), 1.0)
        clipped = clipped or gripper != raw_gripper
        return PandaPositionCommand(tuple(targets), gripper, clipped)
