import unittest
from time import sleep

import numpy as np

from openpi_robot_runtime import ActionChunk, ClosedLoopRuntime, PolicyResponse, RuntimeConfig
from openpi_robot_runtime.official_openpi import OfficialOpenPIDroidClient, OpenPIProtocolError
from openpi_robot_runtime.mock_openpi_bridge import StaticFrameOpenPIBridge
from openpi_robot_runtime.observation_builder import DroidObservation, DroidObservationBuilder, DroidRobotState, RGBFrame
from openpi_robot_runtime.policy import DeterministicFakePolicyClient
from openpi_robot_runtime.remote_client import (
    BoundedRemotePolicyClient,
    OpenPIWebsocketTransportFactory,
    ProcessOwnedTransport,
    RemotePolicyTimeout,
)
from openpi_robot_runtime.simulation import MockDroidRobot


class ClosedLoopRuntimeTests(unittest.TestCase):
    def test_replans_after_execution_horizon_and_clips_commands(self) -> None:
        chunk = ActionChunk.from_rows(
            [
                (2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.0),
                (0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0),
                (0.25, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.5),
            ]
        )
        client = DeterministicFakePolicyClient(
            PolicyResponse(action_chunk=chunk, policy_infer_ms=12.0, server_infer_ms=14.0)
        )
        robot = MockDroidRobot()
        runtime = ClosedLoopRuntime(
            robot=robot,
            policy_client=client,
            config=RuntimeConfig(execution_horizon=2),
        )

        metrics = runtime.run(prompt="move safely", max_execution_steps=5)

        self.assertEqual(metrics.policy_requests, 3)
        self.assertEqual(metrics.executed_actions, 5)
        self.assertEqual(metrics.clipped_actions, 5)
        self.assertEqual(len(client.requests), 3)
        self.assertEqual([item.step_index for item in client.requests], [0, 2, 4])
        self.assertEqual(robot.executed_commands[0].joint_velocity[0], 1.0)
        self.assertEqual(robot.executed_commands[0].gripper_position, 1.0)
        self.assertEqual(robot.executed_commands[1].gripper_position, 0.0)

    def test_rejects_invalid_policy_action_dimension_before_execution(self) -> None:
        client = DeterministicFakePolicyClient(
            PolicyResponse(action_chunk=ActionChunk.from_rows([(0.0,) * 7]))
        )
        robot = MockDroidRobot()
        runtime = ClosedLoopRuntime(robot=robot, policy_client=client, config=RuntimeConfig(execution_horizon=1))

        metrics = runtime.run(prompt="invalid", max_execution_steps=1)
        self.assertEqual(robot.executed_commands, [])
        self.assertEqual(metrics.safe_holds, 1)
        self.assertIn("action_dim=8", metrics.termination_reason or "")

    def test_policy_error_after_one_execution_enters_safe_hold(self) -> None:
        class FailsOnSecondRequest:
            def __init__(self) -> None:
                self.calls = 0

            def infer(self, observation):
                self.calls += 1
                if self.calls == 2:
                    raise ConnectionError("simulated policy disconnect")
                return PolicyResponse(ActionChunk.from_rows([(0.2,) * 8]))

        robot = MockDroidRobot()
        runtime = ClosedLoopRuntime(
            robot=robot,
            policy_client=FailsOnSecondRequest(),
            config=RuntimeConfig(execution_horizon=1),
        )

        metrics = runtime.run(prompt="safe stop", max_execution_steps=3)

        self.assertEqual(metrics.executed_actions, 1)
        self.assertEqual(metrics.safe_holds, 1)
        self.assertIn("simulated policy disconnect", metrics.termination_reason or "")
        self.assertEqual(len(robot.safe_hold_reasons), 1)

    def test_builder_uses_the_public_droid_request_keys(self) -> None:
        frame = RGBFrame(width=224, height=224, data=bytes(224 * 224 * 3))
        request = DroidObservationBuilder().build(
            DroidObservation(frame, frame, DroidRobotState((0.0,) * 7, 0.2), "pick up the block")
        )

        self.assertEqual(
            set(request),
            {
                "observation/exterior_image_1_left",
                "observation/wrist_image_left",
                "observation/joint_position",
                "observation/gripper_position",
                "prompt",
            },
        )
        self.assertEqual(request["observation/gripper_position"], (0.2,))

    def test_remote_boundary_turns_a_slow_request_into_a_timeout(self) -> None:
        class SlowTransport:
            def infer(self, observation):
                sleep(0.03)
                return {"actions": []}

        client = BoundedRemotePolicyClient(SlowTransport(), timeout_seconds=0.001)
        with self.assertRaises(RemotePolicyTimeout):
            client.infer({})

    def test_process_owned_transport_validates_configuration_without_openpi_dependency(self) -> None:
        with self.assertRaises(ValueError):
            ProcessOwnedTransport(OpenPIWebsocketTransportFactory("127.0.0.1", 8000), request_timeout_seconds=0)

    def test_official_adapter_converts_typed_droid_observation_and_response(self) -> None:
        class CapturingTransport:
            def __init__(self) -> None:
                self.request: dict[str, object] | None = None

            def infer(self, observation: dict[str, object]) -> dict[str, object]:
                self.request = observation
                return {
                    "actions": np.zeros((3, 8), dtype=np.float32),
                    "server_timing": {"infer_ms": 13.0},
                    "policy_timing": {"infer_ms": 11.0},
                }

        transport = CapturingTransport()
        client = OfficialOpenPIDroidClient(transport, timeout_seconds=1.0)
        frame = RGBFrame(width=224, height=224, data=bytes(224 * 224 * 3))
        response = client.infer(DroidObservation(frame, frame, DroidRobotState((0.0,) * 7, 0.2), "pick up"))

        assert transport.request is not None
        self.assertEqual(transport.request["observation/exterior_image_1_left"].shape, (224, 224, 3))
        self.assertEqual(transport.request["observation/joint_position"].shape, (7,))
        self.assertEqual(transport.request["observation/gripper_position"].shape, (1,))
        self.assertEqual(response.action_chunk.horizon, 3)
        self.assertEqual(response.server_infer_ms, 13.0)
        self.assertEqual(response.policy_infer_ms, 11.0)

    def test_official_adapter_rejects_bad_action_shape(self) -> None:
        class BadTransport:
            def infer(self, observation: dict[str, object]) -> dict[str, object]:
                return {"actions": np.zeros((2, 7), dtype=np.float32)}

        frame = RGBFrame(width=224, height=224, data=bytes(224 * 224 * 3))
        client = OfficialOpenPIDroidClient(BadTransport(), timeout_seconds=1.0)
        with self.assertRaises(OpenPIProtocolError):
            client.infer(DroidObservation(frame, frame, DroidRobotState((0.0,) * 7, 0.2), "pick up"))

    def test_official_adapter_can_keep_a_thread_confined_transport_in_calling_thread(self) -> None:
        class CapturingTransport:
            def __init__(self) -> None:
                self.called = False

            def infer(self, observation: dict[str, object]) -> dict[str, object]:
                self.called = True
                return {"actions": np.zeros((1, 8), dtype=np.float32)}

        transport = CapturingTransport()
        client = OfficialOpenPIDroidClient(
            transport, timeout_seconds=1.0, transport_is_thread_confined=True
        )
        frame = RGBFrame(width=224, height=224, data=bytes(224 * 224 * 3))
        response = client.infer(DroidObservation(frame, frame, DroidRobotState((0.0,) * 7, 0.2), "pick up"))

        self.assertTrue(transport.called)
        self.assertEqual(response.action_chunk.horizon, 1)

    def test_static_frame_bridge_preserves_receding_horizon_state(self) -> None:
        class TypedClient:
            def __init__(self) -> None:
                self.requests: list[DroidObservation] = []

            def infer(self, observation: DroidObservation) -> PolicyResponse:
                self.requests.append(observation)
                return PolicyResponse(ActionChunk.from_rows([(0.1,) * 8]))

        typed_client = TypedClient()
        frame = RGBFrame(width=224, height=224, data=bytes(224 * 224 * 3))
        bridge = StaticFrameOpenPIBridge(typed_client, exterior_frame=frame, wrist_frame=frame)
        robot = MockDroidRobot()
        runtime = ClosedLoopRuntime(robot=robot, policy_client=bridge, config=RuntimeConfig(execution_horizon=1))

        metrics = runtime.run(prompt="move safely", max_execution_steps=2)

        self.assertEqual(metrics.policy_requests, 2)
        self.assertEqual(len(typed_client.requests), 2)
        self.assertEqual(typed_client.requests[0].state.joint_position, (0.0,) * 7)
        self.assertNotEqual(typed_client.requests[1].state.joint_position, (0.0,) * 7)
        self.assertEqual(typed_client.requests[1].prompt, "move safely")


if __name__ == "__main__":
    unittest.main()
