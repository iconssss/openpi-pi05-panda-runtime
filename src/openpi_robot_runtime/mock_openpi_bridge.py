"""Bridge the mock closed-loop runtime to a typed OpenPI DROID client.

This is intentionally a software-integration harness: it uses explicitly
provided static frames and :class:`MockDroidRobot`, never a camera or robot SDK.
It lets the existing receding-horizon runtime exercise the real policy protocol
without implying a physical-robot evaluation.
"""

from __future__ import annotations

from typing import Protocol

from .contracts import Observation, PolicyResponse
from .observation_builder import DroidObservation, DroidRobotState, RGBFrame


class TypedDroidPolicyClient(Protocol):
    """The typed DROID-policy boundary used by the bridge."""

    def infer(self, observation: DroidObservation) -> PolicyResponse:
        """Return one action chunk for one typed DROID observation."""


class StaticFrameOpenPIBridge:
    """Adapt a mock state observation into one typed OpenPI DROID request.

    The caller must label and retain the source of ``exterior_frame`` and
    ``wrist_frame``.  Production camera capture/preprocessing is deliberately
    outside this bridge.
    """

    def __init__(
        self,
        client: TypedDroidPolicyClient,
        *,
        exterior_frame: RGBFrame,
        wrist_frame: RGBFrame,
    ) -> None:
        self._client = client
        self._exterior_frame = exterior_frame
        self._wrist_frame = wrist_frame
        self.requests: list[DroidObservation] = []

    def infer(self, observation: Observation) -> PolicyResponse:
        request = DroidObservation(
            exterior_image_left=self._exterior_frame,
            wrist_image_left=self._wrist_frame,
            state=DroidRobotState(
                joint_position=observation.joint_position,
                gripper_position=observation.gripper_position,
            ),
            prompt=observation.prompt,
        )
        self.requests.append(request)
        return self._client.infer(request)
