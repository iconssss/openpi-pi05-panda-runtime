"""Create a dependency-free, reproducible Stage 10--12 systems summary."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean


ROOT = Path("/root/shared-nvme/openpi-robot-runtime/results")
OUTPUT = ROOT / "stage13_analysis"


def read(relative: str) -> dict[str, object]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}"


def svg(summary: dict[str, object]) -> str:
    stage11 = summary["stage11"]  # type: ignore[index]
    stage12 = summary["stage12"]  # type: ignore[index]
    warm_single = summary["stage10_warm_single"]  # type: ignore[index]
    cold = summary["stage10_cold_warmup"]  # type: ignore[index]
    values = [
        ("cold warm-up", float(cold["client_round_trip_ms"])),  # type: ignore[index]
        ("warm single", float(warm_single["client_round_trip_ms"])),  # type: ignore[index]
        ("5-cycle mean", float(stage11["mean_client_rtt_ms"])),  # type: ignore[index]
        ("200-cycle mean", float(stage12["client_rtt_mean_ms"])),  # type: ignore[index]
        ("200-cycle p95", float(stage12["client_rtt_p95_ms"])),  # type: ignore[index]
    ]
    width, left, scale = 900, 220, 620
    # Log scale keeps the 33-second JAX warm-up and sub-250-ms hot paths legible.
    import math

    low, high = 1.8, 4.6  # log10 63 ms through 40 s
    rows: list[str] = []
    for index, (label, value) in enumerate(values):
        y = 86 + index * 60
        normalized = max(0.0, min(1.0, (math.log10(value) - low) / (high - low)))
        bar = max(3.0, normalized * scale)
        rows.append(
            f'<text x="15" y="{y + 18}" font-size="16">{label}</text>'
            f'<rect x="{left}" y="{y}" width="{bar:.1f}" height="28" fill="#2864b4"/>'
            f'<text x="{left + bar + 10:.1f}" y="{y + 20}" font-size="15">{value:.2f} ms</text>'
        )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="450" viewBox="0 0 {width} 450">
<rect width="100%" height="100%" fill="white"/>
<text x="15" y="32" font-size="22" font-weight="bold">π0.5 Panda interface: cold vs warm timing</text>
<text x="15" y="56" font-size="13" fill="#444">Logarithmic bar scale. This is a systems latency measurement, not task performance.</text>
{''.join(rows)}
<line x1="{left}" y1="405" x2="{left + scale}" y2="405" stroke="#777"/>
<text x="{left}" y="430" font-size="12">~63 ms</text><text x="{left + scale - 45}" y="430" font-size="12">~40 s</text>
</svg>'''


def main() -> None:
    warmup = read("pi05_panda_warmup.json")
    single = read("pi05_panda_smoke/report.json")
    loop = read("pi05_panda_closed_loop/report.json")
    stress = read("pi05_panda_stress/report.json")
    trace = loop["trace"]  # type: ignore[index]
    steady = trace[1:]  # type: ignore[index]
    condition_summary = [
        {
            "condition": item["condition"],
            "completed_replans": item["completed_replans"],
            "safe_hold": item["safe_hold"],
            "client_rtt_mean_ms": item["client_rtt_mean_ms"],
            "client_rtt_p95_ms": item["client_rtt_p95_ms"],
        }
        for item in stress["conditions"]  # type: ignore[index]
    ]
    summary: dict[str, object] = {
        "scope": "Stage 10--12 systems analysis. No manipulation-success, real-camera, calibration, transfer, or hardware claim.",
        "stage10_cold_warmup": warmup,
        "stage10_warm_single": {
            key: single.get(key)
            for key in ("client_round_trip_ms", "server_infer_ms", "policy_infer_ms", "response_horizon", "executed_action_count", "safe_hold")
        },
        "stage11": {
            "completed_replans": loop["completed_replans"],
            "safe_hold": loop["safe_hold"],
            "mean_client_rtt_ms": mean(float(item["client_round_trip_ms"]) for item in trace),
            "steady_cycles_1_to_4_mean_client_rtt_ms": mean(float(item["client_round_trip_ms"]) for item in steady),
            "clipped_replans": loop["clipped_replans"],
        },
        "stage12": {
            "requested_total_replans": stress["requested_total_replans"],
            "completed_total_replans": stress["completed_total_replans"],
            "safe_hold_conditions": stress["safe_hold_conditions"],
            "clipped_replans": stress["clipped_replans"],
            **stress["aggregate"],  # type: ignore[arg-type,index]
            "conditions": condition_summary,
        },
        "documented_cold_start_safety_event": {
            "count": 1,
            "description": "Before warm-up, a 5-second process-owned request deadline safely held and executed zero Panda actions (Stage 10).",
        },
        "interpretation": [
            "Server warm-up is mandatory before control enablement: first request was ~33.2 seconds, not compatible with a 5-second execution deadline.",
            "After warm-up, the 200-request bounded synthetic-input run had 0 safe holds and 82.61 ms mean / 88.15 ms p95 client RTT.",
            "Synthetic proxy views and a DROID-to-Panda bridge validate system behavior only; they do not establish task or transfer performance.",
        ],
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (OUTPUT / "latency_safety_summary.svg").write_text(svg(summary), encoding="utf-8")
    markdown = f'''# Stage 13 summary

## Timing

| Measurement | Result |
| --- | ---: |
| Cold no-control warm-up | {fmt(float(warmup['client_round_trip_ms']))} ms |
| Warm single Panda request | {fmt(float(single['client_round_trip_ms']))} ms |
| Stage 11 cycles 1--4 mean | {fmt(float(summary['stage11']['steady_cycles_1_to_4_mean_client_rtt_ms']))} ms |
| Stage 12, 200 requests mean / p95 | {fmt(float(summary['stage12']['client_rtt_mean_ms']))} / {fmt(float(summary['stage12']['client_rtt_p95_ms']))} ms |

## Safety and scope

- One pre-warm 5-second deadline event safely held and executed zero Panda actions.
- The Stage 12 stress run completed 200/200 cycles with zero safe holds.
- This is interface evidence under synthetic views, not a Panda task-success or real-world transfer result.

See `summary.json` for all condition-level aggregates and `latency_safety_summary.svg` for the compact figure.
'''
    (OUTPUT / "summary.md").write_text(markdown, encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "stage12_completed": stress["completed_total_replans"]}, indent=2))


if __name__ == "__main__":
    main()
