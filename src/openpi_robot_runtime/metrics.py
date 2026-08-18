"""Small, portable latency artifacts for later quantitative evaluation."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Iterable


@dataclass(frozen=True)
class InferenceMetric:
    request_index: int
    client_round_trip_ms: float
    server_infer_ms: float | None = None
    policy_infer_ms: float | None = None
    outcome: str = "ok"


def write_jsonl(path: Path, metrics: Iterable[InferenceMetric]) -> None:
    """Write a durable, analysis-friendly artifact without third-party packages."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for metric in metrics:
            handle.write(json.dumps(asdict(metric), sort_keys=True) + "\n")


def mean_client_round_trip_ms(metrics: Iterable[InferenceMetric]) -> float | None:
    values = [metric.client_round_trip_ms for metric in metrics if metric.outcome == "ok"]
    return mean(values) if values else None

