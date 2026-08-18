"""Small, explicit policy-output guardrails for the mock runtime."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .adapters import MockDroidCommand


@dataclass(frozen=True)
class SafetyResult:
    command: MockDroidCommand
    clipped: bool


@dataclass(frozen=True)
class DroidLikeSafetyFilter:
    """Bounds velocity and gripper values before the mock SDK is called."""

    max_joint_velocity: float = 1.0
    gripper_min: float = 0.0
    gripper_max: float = 1.0

    def apply(self, command: MockDroidCommand) -> SafetyResult:
        if not all(isfinite(value) for value in (*command.joint_velocity, command.gripper_position)):
            raise ValueError("Safety stop: command contains NaN or Inf.")

        def clip(value: float, lower: float, upper: float) -> float:
            return min(max(value, lower), upper)

        limited_velocity = tuple(
            clip(value, -self.max_joint_velocity, self.max_joint_velocity) for value in command.joint_velocity
        )
        limited_gripper = clip(command.gripper_position, self.gripper_min, self.gripper_max)
        limited = MockDroidCommand(limited_velocity, limited_gripper)
        return SafetyResult(command=limited, clipped=limited != command)

