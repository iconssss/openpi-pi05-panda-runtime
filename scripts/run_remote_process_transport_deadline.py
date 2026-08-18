"""Exercise normal, deadline-safe-hold, and reconnect paths against π0.5."""

from __future__ import annotations

import json
from pathlib import Path

from openpi_robot_runtime.contracts import Observation
from openpi_robot_runtime.mock_openpi_bridge import StaticFrameOpenPIBridge
from openpi_robot_runtime.observation_builder import DroidObservation, DroidRobotState, RGBFrame
from openpi_robot_runtime.official_openpi import OfficialOpenPIDroidClient
from openpi_robot_runtime.remote_client import OpenPIWebsocketTransportFactory, ProcessOwnedTransport
from openpi_robot_runtime.runtime import ClosedLoopRuntime, RuntimeConfig
from openpi_robot_runtime.simulation import MockDroidRobot


def make_observation(frame: RGBFrame) -> DroidObservation:
    return DroidObservation(frame, frame, DroidRobotState((0.0,) * 7, 0.2), "Move to the target location.")


def make_client(*, request_timeout_seconds: float) -> tuple[OfficialOpenPIDroidClient, ProcessOwnedTransport]:
    transport = ProcessOwnedTransport(
        OpenPIWebsocketTransportFactory("127.0.0.1", 8000),
        request_timeout_seconds=request_timeout_seconds,
        startup_timeout_seconds=10.0,
    )
    return (
        OfficialOpenPIDroidClient(
            transport, timeout_seconds=request_timeout_seconds, transport_is_thread_confined=True
        ),
        transport,
    )


def main() -> None:
    frame = RGBFrame(width=224, height=224, data=bytes(224 * 224 * 3))
    normal_client, normal_transport = make_client(request_timeout_seconds=5.0)
    normal = normal_client.infer(make_observation(frame))
    normal_transport.close()

    deadline_client, deadline_transport = make_client(request_timeout_seconds=0.001)
    robot = MockDroidRobot()
    bridge = StaticFrameOpenPIBridge(deadline_client, exterior_frame=frame, wrist_frame=frame)
    metrics = ClosedLoopRuntime(
        robot=robot, policy_client=bridge, config=RuntimeConfig(execution_horizon=1)
    ).run(prompt="Move to the target location.", max_execution_steps=1)
    deadline_transport.close(force=True)

    recovered_client, recovered_transport = make_client(request_timeout_seconds=5.0)
    recovered = recovered_client.infer(make_observation(frame))
    recovered_transport.close()

    report = {
        "scope": "process-owned WebSocket transport test; static frames and MockDroidRobot only; no hardware",
        "normal_response_horizon": normal.action_chunk.horizon,
        "deadline_safe_holds": metrics.safe_holds,
        "deadline_mock_executions": metrics.executed_actions,
        "deadline_termination_reason": metrics.termination_reason,
        "recovered_response_horizon": recovered.action_chunk.horizon,
        "pass": (
            normal.action_chunk.horizon > 0
            and metrics.safe_holds == 1
            and metrics.executed_actions == 0
            and recovered.action_chunk.horizon > 0
        ),
    }
    output = Path("/root/shared-nvme/openpi-robot-runtime/results/process_transport_deadline.json")
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
