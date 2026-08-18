"""Deterministic mock robot used to validate the runtime without a GPU."""

from __future__ import annotations

from dataclasses import dataclass, field

from .adapters import MockDroidCommand
from .contracts import Observation


@dataclass
class MockDroidRobot:
    """A seven-joint integrator, not a physics simulator or real robot claim."""

    joint_position: list[float] = field(default_factory=lambda: [0.0] * 7)
    gripper_position: float = 0.0
    dt_seconds: float = 1.0 / 15.0
    executed_commands: list[MockDroidCommand] = field(default_factory=list)
    safe_hold_reasons: list[str] = field(default_factory=list)

    def observe(self, *, prompt: str, step_index: int) -> Observation:
        return Observation(tuple(self.joint_position), self.gripper_position, prompt, step_index)

    def execute(self, command: MockDroidCommand) -> None:
        self.joint_position = [
            position + velocity * self.dt_seconds
            for position, velocity in zip(self.joint_position, command.joint_velocity, strict=True)
        ]
        self.gripper_position = command.gripper_position
        self.executed_commands.append(command)

    def safe_hold(self, *, reason: str) -> None:
        """Record a zero-velocity hold without advancing the mock state.

        A production embodiment must implement this through its reviewed robot
        SDK/emergency-control semantics. This mock method makes the required
        runtime decision observable without claiming such hardware behavior.
        """

        self.safe_hold_reasons.append(reason)
