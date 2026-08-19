"""Frozen Stage 20 split and diagnostic-only selection rule."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


DIAGNOSTIC_TARGETS = ((0.07, -0.04, 0.01), (0.09, -0.04, 0.02), (0.07, -0.06, 0.03), (0.10, -0.03, 0.01))
FINAL_TEST_TARGETS = ((0.075, -0.045, 0.025), (0.095, -0.055, 0.015), (0.065, -0.065, 0.02), (0.105, -0.035, 0.03))
FIXED_RAW_ACTION = (0.20, -0.20, 0.20, -0.20, 0.20, -0.20, 0.20, 0.5)


@dataclass(frozen=True)
class DlsCondition:
    name: str
    bridge_dt_seconds: float
    episode_steps: int


DLS_DIAGNOSTIC_CONDITIONS = (
    DlsCondition("existing_40", 1.0 / 15.0, 40),
    DlsCondition("existing_120", 1.0 / 15.0, 120),
    DlsCondition("long_dt_120", 0.20, 120),
)


def select_diagnostic_condition(rows: list[dict[str, Any]]) -> str:
    """Apply the pre-registered, deterministic rule to complete diagnostic rows."""
    summaries: list[tuple[tuple[float, ...], str]] = []
    for order, condition in enumerate(DLS_DIAGNOSTIC_CONDITIONS):
        group = [row for row in rows if row["condition"] == condition.name]
        if len(group) != len(DIAGNOSTIC_TARGETS):
            raise ValueError(f"Expected every diagnostic target for {condition.name}.")
        successes = sum(bool(row["success"]) for row in group)
        mean_final = sum(float(row["final_distance_m"]) for row in group) / len(group)
        # min tuple selects: all success, more success, lower distance, shorter, smaller dt, declared order.
        rank = (-float(successes == len(group)), -float(successes), mean_final, condition.episode_steps, condition.bridge_dt_seconds, order)
        summaries.append((rank, condition.name))
    return min(summaries)[1]
