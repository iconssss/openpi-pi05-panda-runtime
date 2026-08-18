"""Compare receding-horizon execution windows using real π0.5 server calls.

This remote-only script is deliberately a systems measurement, not a robot-task
benchmark.  It holds model, prompt, static test frames, mock robot, and total
executed actions fixed; only ``execution_horizon`` changes.
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

from openpi_client.websocket_client_policy import WebsocketClientPolicy

from openpi_robot_runtime.mock_openpi_bridge import StaticFrameOpenPIBridge
from openpi_robot_runtime.observation_builder import RGBFrame
from openpi_robot_runtime.official_openpi import OfficialOpenPIDroidClient
from openpi_robot_runtime.runtime import ClosedLoopRuntime, RuntimeConfig
from openpi_robot_runtime.simulation import MockDroidRobot


def run_condition(*, execution_horizon: int) -> dict[str, object]:
    frame = RGBFrame(width=224, height=224, data=bytes(224 * 224 * 3))
    client = OfficialOpenPIDroidClient(
        WebsocketClientPolicy(host="127.0.0.1", port=8000),
        timeout_seconds=30.0,
        transport_is_thread_confined=True,
    )
    bridge = StaticFrameOpenPIBridge(client, exterior_frame=frame, wrist_frame=frame)
    robot = MockDroidRobot()
    metrics = ClosedLoopRuntime(
        robot=robot,
        policy_client=bridge,
        config=RuntimeConfig(execution_horizon=execution_horizon),
    ).run(prompt="Move the robot arm to the target location.", max_execution_steps=4)
    return {
        "execution_horizon_k": execution_horizon,
        "total_mock_execution_steps": metrics.executed_actions,
        "policy_requests": metrics.policy_requests,
        "clipped_actions": metrics.clipped_actions,
        "client_round_trip_ms": metrics.client_round_trip_ms,
        "client_round_trip_mean_ms": mean(metrics.client_round_trip_ms),
        "server_infer_ms": metrics.server_infer_ms,
        "server_infer_mean_ms": mean(metrics.server_infer_ms),
        "policy_infer_ms": metrics.policy_infer_ms,
        "policy_infer_mean_ms": mean(metrics.policy_infer_ms),
        "final_mock_joint_position": list(robot.observe(prompt="record", step_index=4).joint_position),
    }


def main() -> None:
    report = {
        "scope": "software-only systems ablation: static zero RGB frames and MockDroidRobot; no physical robot",
        "controlled_variables": {
            "policy": "official pi05_droid checkpoint via local WebSocket server",
            "prompt": "Move the robot arm to the target location.",
            "total_mock_execution_steps": 4,
            "image_source": "two static zero 224x224x3 RGB frames",
        },
        "conditions": [run_condition(execution_horizon=k) for k in (1, 2)],
        "interpretation": "k=1 requests a fresh policy chunk before every mock action; k=2 requests half as often. This measures request cadence and latency only, not task quality.",
    }
    output = Path("/root/shared-nvme/openpi-robot-runtime/results/execution_horizon_ablation.json")
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
