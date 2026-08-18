"""Adapter from this project's typed DROID observation to the official OpenPI wire protocol.

The module deliberately receives an ``OpenPITransport`` by dependency injection.
Production supplies ``openpi_client.websocket_client_policy.WebsocketClientPolicy``;
unit tests supply a small fake.  This keeps the Windows-side project package free
of a heavyweight OpenPI/GPU dependency while making the serialization boundary
explicit and testable.
"""

from __future__ import annotations

from numbers import Real
from typing import Any

from .contracts import ActionChunk, PolicyResponse
from .observation_builder import DroidObservation, DroidObservationBuilder, RGBFrame
from .remote_client import BoundedRemotePolicyClient, OpenPITransport, RemotePolicyError


class OpenPIProtocolError(RuntimeError):
    """A response violates the public OpenPI DROID policy contract."""


class OfficialOpenPIDroidClient:
    """Typed robot-side client over the official synchronous WebSocket transport.

    This class does not execute a robot command.  It only constructs an OpenPI
    request, applies a robot-side deadline, and decodes one fresh action chunk.
    The caller remains responsible for embodiment adaptation, safety filtering,
    and receding-horizon execution.
    """

    def __init__(
        self,
        transport: OpenPITransport,
        *,
        timeout_seconds: float,
        transport_is_thread_confined: bool = False,
    ) -> None:
        self._builder = DroidObservationBuilder()
        self._transport = transport
        self._transport_is_thread_confined = transport_is_thread_confined
        self._bounded_transport = BoundedRemotePolicyClient(transport, timeout_seconds=timeout_seconds)

    def infer(self, observation: DroidObservation) -> PolicyResponse:
        request = self._to_wire_observation(observation)
        if self._transport_is_thread_confined:
            # OpenPI's synchronous WebsocketClientPolicy opens its socket during
            # construction. Its send/recv pair must therefore remain on that
            # owning thread. A hard timeout needs a process-owned/cancellable
            # transport, not a ThreadPool wrapper around this connection.
            try:
                payload = self._transport.infer(request)
            except Exception as error:
                raise RemotePolicyError(
                    "Thread-confined OpenPI policy request failed: "
                    f"{type(error).__name__}: {error}"
                ) from error
        else:
            payload = self._bounded_transport.infer(request).payload
        return self._to_policy_response(payload)

    def _to_wire_observation(self, observation: DroidObservation) -> dict[str, object]:
        request = self._builder.build(observation)
        return {
            "observation/exterior_image_1_left": self._frame_to_numpy(
                request["observation/exterior_image_1_left"]
            ),
            "observation/wrist_image_left": self._frame_to_numpy(request["observation/wrist_image_left"]),
            "observation/joint_position": self._float_array(request["observation/joint_position"], expected_size=7),
            "observation/gripper_position": self._float_array(
                request["observation/gripper_position"], expected_size=1
            ),
            "prompt": request["prompt"],
        }

    @staticmethod
    def _frame_to_numpy(frame: object) -> Any:
        if not isinstance(frame, RGBFrame):
            raise TypeError("DroidObservationBuilder returned an unexpected image type.")
        import numpy as np

        return np.frombuffer(frame.data, dtype=np.uint8).reshape((frame.height, frame.width, frame.channels)).copy()

    @staticmethod
    def _float_array(values: object, *, expected_size: int) -> Any:
        import numpy as np

        array = np.asarray(values, dtype=np.float32)
        if array.shape != (expected_size,):
            raise ValueError(f"Expected a float vector of shape ({expected_size},), got {array.shape}.")
        return array

    @staticmethod
    def _to_policy_response(payload: dict[str, object]) -> PolicyResponse:
        actions = payload.get("actions")
        if actions is None:
            raise OpenPIProtocolError("OpenPI response has no 'actions' field.")
        try:
            rows = actions.tolist() if hasattr(actions, "tolist") else actions
            chunk = ActionChunk.from_rows(rows)  # type: ignore[arg-type]
            chunk.validate()
        except (TypeError, ValueError) as error:
            raise OpenPIProtocolError("OpenPI response actions are not a finite (H, 8) chunk.") from error
        return PolicyResponse(
            action_chunk=chunk,
            server_infer_ms=OfficialOpenPIDroidClient._timing(payload, "server_timing", "infer_ms"),
            policy_infer_ms=OfficialOpenPIDroidClient._timing(payload, "policy_timing", "infer_ms"),
        )

    @staticmethod
    def _timing(payload: dict[str, object], group: str, key: str) -> float | None:
        timing = payload.get(group)
        if timing is None:
            return None
        if not isinstance(timing, dict) or key not in timing or not isinstance(timing[key], Real):
            raise OpenPIProtocolError(f"OpenPI response field '{group}.{key}' is invalid.")
        return float(timing[key])
