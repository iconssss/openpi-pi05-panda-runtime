"""Run a safe, software-only OpenPI pi05_droid closed-loop integration smoke test.

This script is designed for the configured remote container.  It sends typed
DROID requests to an already-running official OpenPI WebSocket server, but its
camera frames are static zero frames and execution is confined to MockDroidRobot.
It never imports or calls a physical robot SDK.
"""

from __future__ import annotations

import json
from pathlib import Path

from openpi_client.websocket_client_policy import WebsocketClientPolicy

from openpi_robot_runtime.mock_openpi_bridge import StaticFrameOpenPIBridge
from openpi_robot_runtime.observation_builder import RGBFrame
from openpi_robot_runtime.official_openpi import OfficialOpenPIDroidClient
from openpi_robot_runtime.runtime import ClosedLoopRuntime, RuntimeConfig
from openpi_robot_runtime.simulation import MockDroidRobot


def main() -> None:
    frame = RGBFrame(width=224, height=224, data=bytes(224 * 224 * 3))
    remote_policy = OfficialOpenPIDroidClient(
        WebsocketClientPolicy(host="127.0.0.1", port=8000),
        timeout_seconds=30.0,
        transport_is_thread_confined=True,
    )
    bridge = StaticFrameOpenPIBridge(
        remote_policy, exterior_frame=frame, wrist_frame=frame
    )
    robot = MockDroidRobot()
    runtime = ClosedLoopRuntime(
        robot=robot,
        policy_client=bridge,
        config=RuntimeConfig(execution_horizon=1),
    )
    metrics = runtime.run(
        prompt="Move the robot arm to the target location.", max_execution_steps=2
    )
    report = {
        "scope": "software-only integration smoke test; static zero images and MockDroidRobot; no physical robot",
        "policy_requests": metrics.policy_requests,
        "executed_actions": metrics.executed_actions,
        "clipped_actions": metrics.clipped_actions,
        "client_round_trip_ms": metrics.client_round_trip_ms,
        "server_infer_ms": metrics.server_infer_ms,
        "policy_infer_ms": metrics.policy_infer_ms,
        "mock_commands": [
            {
                "joint_velocity": list(command.joint_velocity),
                "gripper_position": command.gripper_position,
            }
            for command in robot.executed_commands
        ],
        "reobserved_joint_position": list(robot.observe(prompt="record", step_index=2).joint_position),
    }
    output = Path("/root/shared-nvme/openpi-robot-runtime/results/project_runtime_closed_loop_smoke.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
