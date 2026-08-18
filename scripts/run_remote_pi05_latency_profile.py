"""Profile official pi05_droid inference latency with a fixed test contract.

The script intentionally measures service performance only. It uses static test
frames, never a robot SDK, and reports summary statistics rather than claiming
manipulation quality.
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean, median
from time import perf_counter

from openpi_client.websocket_client_policy import WebsocketClientPolicy

from openpi_robot_runtime.observation_builder import DroidObservation, DroidRobotState, RGBFrame
from openpi_robot_runtime.official_openpi import OfficialOpenPIDroidClient

WARMUP_REQUESTS = 3
MEASURED_REQUESTS = 60
PROMPTS = (
    "Move the robot arm to the target location.",
    "Pick up the object carefully.",
    "Place the object on the marked area.",
)


def summary(samples: list[float]) -> dict[str, float]:
    ordered = sorted(samples)

    def percentile(fraction: float) -> float:
        index = round((len(ordered) - 1) * fraction)
        return ordered[index]

    return {
        "count": len(samples),
        "mean_ms": mean(samples),
        "median_ms": median(samples),
        "p95_ms": percentile(0.95),
        "min_ms": ordered[0],
        "max_ms": ordered[-1],
    }


def main() -> None:
    frame = RGBFrame(width=224, height=224, data=bytes(224 * 224 * 3))
    client = OfficialOpenPIDroidClient(
        WebsocketClientPolicy(host="127.0.0.1", port=8000),
        timeout_seconds=30.0,
        transport_is_thread_confined=True,
    )

    def request(index: int):
        observation = DroidObservation(
            exterior_image_left=frame,
            wrist_image_left=frame,
            state=DroidRobotState((0.0,) * 7, 0.2),
            prompt=PROMPTS[index % len(PROMPTS)],
        )
        started = perf_counter()
        response = client.infer(observation)
        return (perf_counter() - started) * 1000, response

    for index in range(WARMUP_REQUESTS):
        request(index)

    client_rtt: list[float] = []
    server: list[float] = []
    policy: list[float] = []
    first_actions: dict[str, list[float]] = {}
    for index in range(MEASURED_REQUESTS):
        elapsed, response = request(index)
        client_rtt.append(elapsed)
        if response.server_infer_ms is not None:
            server.append(response.server_infer_ms)
        if response.policy_infer_ms is not None:
            policy.append(response.policy_infer_ms)
        prompt = PROMPTS[index % len(PROMPTS)]
        first_actions.setdefault(prompt, list(response.action_chunk.actions[0]))

    report = {
        "scope": "inference-service performance profile only; static zero RGB frames; no physical robot or task-quality claim",
        "warmup_requests": WARMUP_REQUESTS,
        "measured_requests": MEASURED_REQUESTS,
        "prompt_count": len(PROMPTS),
        "client_round_trip": summary(client_rtt),
        "server_infer": summary(server),
        "policy_infer": summary(policy),
        "first_action_by_prompt": first_actions,
        "method_note": "Requests are sequential over one official synchronous WebSocket connection; results are not throughput under concurrent clients.",
    }
    output = Path("/root/shared-nvme/openpi-robot-runtime/results/pi05_droid_latency_profile.json")
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
