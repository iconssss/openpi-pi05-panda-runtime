"""Robot-side construction and validation of a π0.5-DROID request.

This module describes the boundary before serialization. It deliberately does
not resize or encode images: camera preprocessing belongs to the robot-side
capture pipeline and must be made explicit for the selected hardware.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RGBFrame:
    """A preprocessed uint8 HWC RGB image represented without image libraries."""

    width: int
    height: int
    data: bytes
    channels: int = 3

    def validate(self) -> None:
        if (self.width, self.height, self.channels) != (224, 224, 3):
            raise ValueError("π0.5-DROID request images must be preprocessed to 224x224 RGB.")
        if len(self.data) != self.width * self.height * self.channels:
            raise ValueError("RGBFrame byte length does not match HWC dimensions.")


@dataclass(frozen=True)
class DroidRobotState:
    """The public DROID input contract used by OpenPI's current policy transform."""

    joint_position: tuple[float, ...]
    gripper_position: float

    def validate(self) -> None:
        if len(self.joint_position) != 7:
            raise ValueError("π0.5-DROID requires exactly 7 joint positions.")


@dataclass(frozen=True)
class DroidObservation:
    """Typed robot-side data prior to conversion to an OpenPI request dictionary."""

    exterior_image_left: RGBFrame
    wrist_image_left: RGBFrame
    state: DroidRobotState
    prompt: str


class DroidObservationBuilder:
    """Produces the exact public keys consumed by OpenPI's DroidInputs transform."""

    def build(self, observation: DroidObservation) -> dict[str, object]:
        observation.exterior_image_left.validate()
        observation.wrist_image_left.validate()
        observation.state.validate()
        if not observation.prompt.strip():
            raise ValueError("A non-empty language prompt is required.")
        return {
            "observation/exterior_image_1_left": observation.exterior_image_left,
            "observation/wrist_image_left": observation.wrist_image_left,
            "observation/joint_position": observation.state.joint_position,
            "observation/gripper_position": (observation.state.gripper_position,),
            "prompt": observation.prompt,
        }

