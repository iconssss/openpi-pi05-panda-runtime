"""Protocol constants and pure helpers for the Stage 18 held-out study."""

from __future__ import annotations

from dataclasses import dataclass


STAGE17_HELD_OUT_TARGET_INDICES = (8, 9, 10, 11)
STAGE18_EPISODE_STEPS = 40
ADAPTER_SEEDS = (11, 22, 33)


@dataclass(frozen=True)
class EvaluationVariant:
    """A pre-registered Stage 18 evaluation arm."""

    name: str
    kind: str
    adapter_seed: int | None = None


def evaluation_variants() -> tuple[EvaluationVariant, ...]:
    """Return every required arm; this intentionally has no result selection."""
    return (
        EvaluationVariant("raw_pi05_identity", "pi05_identity"),
        *(EvaluationVariant(f"residual_adapter_seed_{seed}", "residual_adapter", seed) for seed in ADAPTER_SEEDS),
        EvaluationVariant("dls_oracle", "dls_oracle"),
    )


def combine_residual_action(
    raw_action: tuple[float, ...], residual: tuple[float, ...]
) -> tuple[float, ...]:
    """Add a seven-joint residual while preserving the policy gripper value."""
    if len(raw_action) != 8 or len(residual) != 7:
        raise ValueError("Stage 18 requires an 8-D raw action and 7-D residual.")
    return tuple(raw + delta for raw, delta in zip(raw_action[:7], residual, strict=True)) + (raw_action[7],)
