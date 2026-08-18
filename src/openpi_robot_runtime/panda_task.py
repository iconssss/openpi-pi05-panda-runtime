"""Task-independent geometric metric for the controlled Panda reach scene."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt


@dataclass(frozen=True)
class ReachMetric:
    target_position: tuple[float, float, float]
    threshold_meters: float = 0.04

    def __post_init__(self) -> None:
        if len(self.target_position) != 3 or self.threshold_meters <= 0:
            raise ValueError("Reach metric needs a 3-D target and positive threshold.")

    def distance_meters(self, hand_position: tuple[float, float, float]) -> float:
        if len(hand_position) != 3:
            raise ValueError("Reach metric needs a 3-D hand position.")
        return sqrt(sum((hand - target) ** 2 for hand, target in zip(hand_position, self.target_position, strict=True)))

    def success(self, hand_position: tuple[float, float, float]) -> bool:
        return self.distance_meters(hand_position) <= self.threshold_meters
