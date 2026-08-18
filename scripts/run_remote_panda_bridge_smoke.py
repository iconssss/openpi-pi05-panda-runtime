"""Headless Panda bridge smoke: typed 8-D action -> MuJoCo position controls.

The two rendered views are synthetic free-camera proxies.  They verify that a
DROID-shaped request can be constructed, not camera calibration or policy
transfer to Panda.
"""

from __future__ import annotations

import json
from pathlib import Path

import imageio.v3 as iio
import mujoco
import numpy as np

from openpi_robot_runtime.observation_builder import DroidObservation, DroidRobotState, RGBFrame
from openpi_robot_runtime.panda_bridge import DroidLikePandaActionBridge


ASSET_ROOT = Path("/root/shared-nvme/openpi-robot-runtime/assets/panda_menagerie/franka_emika_panda")
RESULT_ROOT = Path("/root/shared-nvme/openpi-robot-runtime/results/panda_bridge_smoke")


def resize_to_frame(image: np.ndarray) -> RGBFrame:
    # Nearest-neighbor sampling is a deliberately simple, documented proxy.
    rows = np.linspace(0, image.shape[0] - 1, 224).astype(np.intp)
    columns = np.linspace(0, image.shape[1] - 1, 224).astype(np.intp)
    resized = image[rows][:, columns, :3].astype(np.uint8, copy=False)
    return RGBFrame(width=224, height=224, data=resized.tobytes())


def free_camera(*, azimuth: float, elevation: float, distance: float, lookat: tuple[float, float, float]) -> mujoco.MjvCamera:
    camera = mujoco.MjvCamera()
    camera.type = mujoco.mjtCamera.mjCAMERA_FREE
    camera.azimuth = azimuth
    camera.elevation = elevation
    camera.distance = distance
    camera.lookat[:] = lookat
    return camera


def main() -> None:
    model = mujoco.MjModel.from_xml_path(str(ASSET_ROOT / "scene.xml"))
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)

    arm_joint_names = tuple(f"joint{index}" for index in range(1, 8))
    arm_joint_ids = tuple(mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name) for name in arm_joint_names)
    if any(joint_id < 0 for joint_id in arm_joint_ids):
        raise RuntimeError(f"Missing expected Panda joints: {arm_joint_names}")
    arm_qpos_addresses = tuple(int(model.jnt_qposadr[joint_id]) for joint_id in arm_joint_ids)
    arm_limits = tuple(tuple(float(value) for value in model.jnt_range[joint_id]) for joint_id in arm_joint_ids)

    actuator_joint_ids = tuple(int(model.actuator_trnid[index, 0]) for index in range(model.nu))
    arm_actuator_indices = tuple(actuator_joint_ids.index(joint_id) for joint_id in arm_joint_ids)
    # The eighth Panda actuator is a tendon transmission.  Its ``trnid`` is a
    # tendon ID, not a joint ID, so numerical IDs can overlap with ``joint1``.
    # Determine arm actuators first, then treat only the remaining actuator(s)
    # as gripper controls.
    finger_actuator_indices = tuple(index for index in range(model.nu) if index not in arm_actuator_indices)
    if not finger_actuator_indices:
        raise RuntimeError("No Panda gripper control remains after resolving seven arm actuators.")

    bridge = DroidLikePandaActionBridge(arm_limits)
    action = (0.20, -0.15, 0.10, 0.05, -0.05, 0.10, -0.10, 0.70)
    before = tuple(float(data.qpos[address]) for address in arm_qpos_addresses)
    command = bridge.to_position_command(current_joint_positions=before, droid_like_action=action)
    for actuator, target in zip(arm_actuator_indices, command.joint_position_targets, strict=True):
        data.ctrl[actuator] = target
    for actuator in finger_actuator_indices:
        low, high = (float(value) for value in model.actuator_ctrlrange[actuator])
        data.ctrl[actuator] = low + command.gripper_normalized * (high - low)
    for _ in range(15):
        mujoco.mj_step(model, data)
    after = tuple(float(data.qpos[address]) for address in arm_qpos_addresses)

    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    renderer = mujoco.Renderer(model, height=256, width=256)
    exterior = free_camera(azimuth=140, elevation=-25, distance=2.0, lookat=(0.0, 0.0, 0.45))
    wrist_proxy = free_camera(azimuth=30, elevation=-10, distance=0.65, lookat=(0.0, 0.0, 0.45))
    renderer.update_scene(data, camera=exterior)
    exterior_image = renderer.render().copy()
    renderer.update_scene(data, camera=wrist_proxy)
    wrist_image = renderer.render().copy()
    iio.imwrite(RESULT_ROOT / "exterior_proxy.png", exterior_image)
    iio.imwrite(RESULT_ROOT / "wrist_proxy.png", wrist_image)

    observation = DroidObservation(
        exterior_image_left=resize_to_frame(exterior_image),
        wrist_image_left=resize_to_frame(wrist_image),
        state=DroidRobotState(after, command.gripper_normalized),
        prompt="Move the Panda end effector safely in simulation.",
    )
    observation.exterior_image_left.validate()
    observation.wrist_image_left.validate()
    observation.state.validate()
    report = {
        "scope": "Panda simulator action/observation bridge smoke only; synthetic cameras; no OpenPI policy call or transfer claim",
        "xml": str(ASSET_ROOT / "scene.xml"),
        "model": {"nq": model.nq, "nv": model.nv, "nu": model.nu, "ncam": model.ncam},
        "arm_joint_names": arm_joint_names,
        "arm_actuator_indices": arm_actuator_indices,
        "gripper_actuator_indices": finger_actuator_indices,
        "droid_like_action": action,
        "position_targets": command.joint_position_targets,
        "joint_positions_before": before,
        "joint_positions_after_15_steps": after,
        "bridge_clipped": command.clipped,
        "droid_request_proxy": {"image_shape": [224, 224, 3], "joint_position_shape": [7], "gripper_position_shape": [1]},
        "image_artifacts": [str(RESULT_ROOT / "exterior_proxy.png"), str(RESULT_ROOT / "wrist_proxy.png")],
    }
    (RESULT_ROOT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
