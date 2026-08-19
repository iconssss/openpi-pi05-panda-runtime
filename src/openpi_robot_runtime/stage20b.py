"""Frozen target split and diagnostic selection for Stage 20B."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

DEVELOPMENT_TARGETS = ((0.06, -0.03, 0.01), (0.08, -0.05, 0.02), (0.09, -0.03, 0.015), (0.07, -0.06, 0.02))
FINAL_TEST_TARGETS = ((0.065, -0.035, 0.015), (0.085, -0.045, 0.020), (0.075, -0.055, 0.010), (0.095, -0.040, 0.020))
TARGET_SEED = 20260819

@dataclass(frozen=True)
class ContractCondition:
    name: str; damping: float; max_joint_velocity: float; control_dt_seconds: float; episode_steps: int; slowdown_radius_m: float | None

CONDITIONS = (
    ContractCondition("stage20_reference", 0.010, 1.00, 0.20, 120, None),
    ContractCondition("damped_slow_200", 0.032, 0.50, 0.10, 200, 0.08),
    ContractCondition("low_speed_long_240", 0.010, 0.35, 0.10, 240, 0.08),
    ContractCondition("medium_slow_180", 0.022, 0.50, 0.15, 180, 0.06),
)

def select_condition(rows: list[dict[str, Any]]) -> str:
    ranks = []
    for order, condition in enumerate(CONDITIONS):
        group = [row for row in rows if row["condition"] == condition.name]
        if len(group) != len(DEVELOPMENT_TARGETS): raise ValueError(f"Incomplete development group: {condition.name}")
        ranks.append(((-sum(bool(row["success"]) for row in group), sum(float(row["final_distance_m"]) for row in group) / len(group), sum(int(row["bridge_clipped_steps"]) for row in group), order), condition.name))
    return min(ranks)[1]
