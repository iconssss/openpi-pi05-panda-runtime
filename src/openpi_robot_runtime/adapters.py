"""Embodiment-specific conversion after a policy returns an action chunk."""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import DROID_LIKE_ACTION_DIM


@dataclass(frozen=True)
class MockDroidCommand:
    """Mock SDK command: 7 joint velocities and an absolute gripper position."""

    joint_velocity: tuple[float, ...]
    gripper_position: float


class MockDroidAdapter:
    """Maps the selected DROID-like policy contract to a mock robot command.

    The official DROID example describes this contract as 7 joint velocities
    plus 1 gripper position. A real robot adapter would replace this class,
    documenting frames, units, limits, and its SDK command type.
    """

    def to_command(self, action: tuple[float, ...]) -> MockDroidCommand:
        if len(action) != DROID_LIKE_ACTION_DIM:
            raise ValueError(f"MockDroidAdapter requires {DROID_LIKE_ACTION_DIM} action values.")
        return MockDroidCommand(joint_velocity=action[:7], gripper_position=action[7])

