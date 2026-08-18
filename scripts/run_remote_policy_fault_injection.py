"""Verify fail-safe hold after a real π0.5 request and a controlled fault.

One request is sent to the official server. The wrapper then raises a synthetic
connection error before the next request. This verifies runtime fault handling
without intentionally breaking the shared server or connecting hardware.
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


class FailAfterOneSuccessfulRequest:
    def __init__(self, client: OfficialOpenPIDroidClient) -> None:
        self._client = client
        self.calls = 0

    def infer(self, observation):
        self.calls += 1
        if self.calls > 1:
            raise ConnectionError("controlled fault injection after one confirmed OpenPI response")
        return self._client.infer(observation)


def main() -> None:
    frame = RGBFrame(width=224, height=224, data=bytes(224 * 224 * 3))
    official_client = OfficialOpenPIDroidClient(
        WebsocketClientPolicy(host="127.0.0.1", port=8000),
        timeout_seconds=30.0,
        transport_is_thread_confined=True,
    )
    faulting_client = FailAfterOneSuccessfulRequest(official_client)
    robot = MockDroidRobot()
    bridge = StaticFrameOpenPIBridge(
        faulting_client, exterior_frame=frame, wrist_frame=frame
    )
    metrics = ClosedLoopRuntime(
        robot=robot,
        policy_client=bridge,
        config=RuntimeConfig(execution_horizon=1),
    ).run(prompt="Move the robot arm to the target location.", max_execution_steps=3)

    report = {
        "scope": "software-only fail-safe test; one real OpenPI response followed by a controlled client-side fault; no hardware",
        "policy_attempts": faulting_client.calls,
        "confirmed_mock_executions": metrics.executed_actions,
        "safe_holds": metrics.safe_holds,
        "termination_reason": metrics.termination_reason,
        "safe_hold_reasons": robot.safe_hold_reasons,
        "mock_command_count": len(robot.executed_commands),
        "pass": metrics.executed_actions == 1 and metrics.safe_holds == 1,
    }
    output = Path("/root/shared-nvme/openpi-robot-runtime/results/policy_fault_injection.json")
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
