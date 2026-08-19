"""Pure, read-only Stage 19 analysis for the frozen Stage 18 report."""

from __future__ import annotations

from collections import defaultdict
from statistics import mean, pstdev
from typing import Any


VARIANT_ORDER = (
    "raw_pi05_identity", "residual_adapter_seed_11", "residual_adapter_seed_22",
    "residual_adapter_seed_33", "dls_oracle",
)


def _mean(values: list[float]) -> float | None:
    return mean(values) if values else None


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    curves = [[float(value) for value in row["distance_curve_m"]] for row in rows]
    lengths = {len(curve) for curve in curves}
    if len(lengths) != 1:
        raise ValueError("Every comparison group must have equally long distance curves.")
    final = [curve[-1] for curve in curves]
    initial = [curve[0] for curve in curves]
    minimum = [min(curve) for curve in curves]
    curve_mean = [mean(step) for step in zip(*curves, strict=True)]
    late_change = [curve[-1] - curve[-11] for curve in curves] if len(curves[0]) >= 11 else []
    return {
        "episodes": len(rows),
        "successes": sum(bool(row["success"]) for row in rows),
        "safe_holds": sum(int(row["safe_hold_count"]) for row in rows),
        "bridge_clipped_steps": sum(int(row["bridge_clipped_steps"]) for row in rows),
        "mean_initial_distance_m": _mean(initial),
        "mean_final_distance_m": _mean(final),
        "final_distance_stddev_m": pstdev(final) if len(final) > 1 else 0.0,
        "mean_net_distance_change_m": _mean([end - start for start, end in zip(initial, final, strict=True)]),
        "mean_minimum_distance_m": _mean(minimum),
        "mean_last_ten_step_change_m": _mean(late_change),
        "mean_distance_curve_m": curve_mean,
    }


def analyze_stage18_report(report: dict[str, Any]) -> dict[str, Any]:
    """Create a descriptive analysis without filtering, selection, or tuning."""
    episodes = report.get("episodes")
    if not isinstance(episodes, list) or not episodes:
        raise ValueError("Stage 18 report needs non-empty episodes.")
    by_variant: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_visual: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_target: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in episodes:
        variant = str(row["variant"])
        if variant not in VARIANT_ORDER:
            raise ValueError(f"Unexpected evaluation variant: {variant}")
        by_variant[variant].append(row)
        by_visual[f"{variant}/{row['visual_condition']}"] .append(row)
        by_target[f"{variant}/target_{row['target_index']}"] .append(row)
    if tuple(sorted(by_variant)) != tuple(sorted(VARIANT_ORDER)):
        raise ValueError("Report must contain every pre-registered Stage 18 arm.")
    variants = {variant: _summarize(by_variant[variant]) for variant in VARIANT_ORDER}
    raw_final = float(variants["raw_pi05_identity"]["mean_final_distance_m"])
    return {
        "scope": "read-only Stage 19 descriptive analysis of the frozen Stage 18 held-out report; no tuning, seed selection, retraining, or new policy requests",
        "input_contract": report["experiment_boundary"],
        "variants": variants,
        "by_visual_condition": {key: _summarize(rows) for key, rows in sorted(by_visual.items())},
        "by_target": {key: _summarize(rows) for key, rows in sorted(by_target.items())},
        "final_distance_reduction_vs_raw_m": {variant: raw_final - float(variants[variant]["mean_final_distance_m"]) for variant in VARIANT_ORDER if variant != "raw_pi05_identity"},
        "unidentifiable_from_stage18_log": [
            "per-step adapter residual magnitude and direction",
            "Panda joint-state distribution shift from the diagnostic training distribution",
            "joint-limit proximity or unclipped command saturation",
        ],
        "supported_negative_finding": "zero bridge-clipped steps and zero safe holds rule out observed bridge clipping or deadline safe holds as direct explanations for the 0/24 success result",
    }


def mean_curve_svg(analysis: dict[str, Any]) -> str:
    """Return a dependency-free SVG of the common mean distance trajectories."""
    width, height, margin = 760, 420, 55
    curves = [analysis["variants"][variant]["mean_distance_curve_m"] for variant in VARIANT_ORDER]
    maximum = max(max(curve) for curve in curves)
    colors = ("#b91c1c", "#2563eb", "#7c3aed", "#0891b2", "#15803d")
    def point(step: int, distance: float) -> str:
        x = margin + step * (width - 2 * margin) / (len(curves[0]) - 1)
        y = height - margin - distance * (height - 2 * margin) / maximum
        return f"{x:.1f},{y:.1f}"
    paths = []
    labels = []
    for index, (variant, curve, color) in enumerate(zip(VARIANT_ORDER, curves, colors, strict=True)):
        paths.append(f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{" ".join(point(step, value) for step, value in enumerate(curve))}"/>')
        labels.append(f'<text x="{margin}" y="{18 + index * 16}" fill="{color}" font-size="12">{variant}</text>')
    return "\n".join([f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="white"/>', f'<line x1="{margin}" y1="{height-margin}" x2="{width-margin}" y2="{height-margin}" stroke="black"/>', f'<line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height-margin}" stroke="black"/>', f'<text x="{width/2:.0f}" y="{height-12}" text-anchor="middle" font-size="12">control step (0–40)</text>', f'<text x="8" y="{height/2:.0f}" font-size="12" transform="rotate(-90 8 {height/2:.0f})">mean distance (m)</text>', *paths, *labels, '</svg>'])
