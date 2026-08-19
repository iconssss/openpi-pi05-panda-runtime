"""Leakage-safe feature construction for the frozen Stage 21A probe."""
from __future__ import annotations

def action_feature(chunk: tuple[tuple[float, ...], ...]) -> tuple[float, ...]:
    if not chunk or any(len(action) != 8 for action in chunk): raise ValueError("Expected finite non-empty (H, 8) action chunk.")
    return tuple(chunk[0]) + tuple(sum(action[index] for action in chunk) / len(chunk) for index in range(8))

def split_for_target(target_id: int) -> str:
    if not 0 <= target_id < 24: raise ValueError("Stage 21A target ID out of range.")
    return "train" if target_id < 16 else "validation" if target_id < 20 else "test"
