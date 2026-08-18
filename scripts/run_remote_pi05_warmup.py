"""Warm the loaded π0.5 server without issuing any simulator control."""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter

from openpi_client.websocket_client_policy import WebsocketClientPolicy

from openpi_robot_runtime.observation_builder import DroidObservation, DroidRobotState, RGBFrame
from openpi_robot_runtime.official_openpi import OfficialOpenPIDroidClient


def main() -> None:
    frame = RGBFrame(224, 224, bytes(224 * 224 * 3))
    observation = DroidObservation(frame, frame, DroidRobotState((0.0,) * 7, 0.5), "Warm up policy server.")
    client = OfficialOpenPIDroidClient(
        WebsocketClientPolicy(host="127.0.0.1", port=8000),
        timeout_seconds=30.0,
        transport_is_thread_confined=True,
    )
    started = perf_counter()
    response = client.infer(observation)
    report = {
        "scope": "server warm-up only; static zero images; no Panda control",
        "client_round_trip_ms": (perf_counter() - started) * 1000,
        "response_horizon": response.action_chunk.horizon,
        "server_infer_ms": response.server_infer_ms,
        "policy_infer_ms": response.policy_infer_ms,
    }
    target = Path("/root/shared-nvme/openpi-robot-runtime/results/pi05_panda_warmup.json")
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
