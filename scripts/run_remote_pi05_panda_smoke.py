"""One bounded π0.5 request with synthetic Panda observations.

This is an embodiment-interface smoke, not a Panda policy-transfer benchmark.
The model receives two synthetic free-camera proxy images.  Exactly the first
returned action is eligible for simulator execution; a transport error records
a safe hold and sends no Panda control.
"""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter

import mujoco
import numpy as np

from openpi_robot_runtime.observation_builder import DroidObservation, DroidRobotState, RGBFrame
from openpi_robot_runtime.official_openpi import OfficialOpenPIDroidClient
from openpi_robot_runtime.panda_bridge import DroidLikePandaActionBridge
from openpi_robot_runtime.remote_client import OpenPIWebsocketTransportFactory, ProcessOwnedTransport


ASSET_ROOT = Path("/root/shared-nvme/openpi-robot-runtime/assets/panda_menagerie/franka_emika_panda")
RESULT_ROOT = Path("/root/shared-nvme/openpi-robot-runtime/results/pi05_panda_smoke")


def make_frame(image: np.ndarray) -> RGBFrame:
    rows = np.linspace(0, image.shape[0] - 1, 224).astype(np.intp)
    columns = np.linspace(0, image.shape[1] - 1, 224).astype(np.intp)
    resized = image[rows][:, columns, :3].astype(np.uint8, copy=False)
    return RGBFrame(224, 224, resized.tobytes())


def make_camera(*, azimuth: float, elevation: float, distance: float) -> mujoco.MjvCamera:
    camera = mujoco.MjvCamera()
    camera.type = mujoco.mjtCamera.mjCAMERA_FREE
    camera.azimuth, camera.elevation, camera.distance = azimuth, elevation, distance
    camera.lookat[:] = (0.0, 0.0, 0.45)
    return camera


def panda_handles(model: mujoco.MjModel) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...], tuple[tuple[float, float], ...]]:
    joint_ids = tuple(mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, f"joint{i}") for i in range(1, 8))
    if any(identifier < 0 for identifier in joint_ids):
        raise RuntimeError("Expected Panda joint1..joint7 are unavailable.")
    qpos_addresses = tuple(int(model.jnt_qposadr[identifier]) for identifier in joint_ids)
    actuator_joint_ids = tuple(int(model.actuator_trnid[index, 0]) for index in range(model.nu))
    arm_actuators = tuple(actuator_joint_ids.index(identifier) for identifier in joint_ids)
    gripper_actuators = tuple(index for index in range(model.nu) if index not in arm_actuators)
    if not gripper_actuators:
        raise RuntimeError("Panda model has no control remaining for the gripper.")
    limits = tuple(tuple(float(value) for value in model.jnt_range[identifier]) for identifier in joint_ids)
    return qpos_addresses, arm_actuators, gripper_actuators, limits


def main() -> None:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    model = mujoco.MjModel.from_xml_path(str(ASSET_ROOT / "scene.xml"))
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    qpos_addresses, arm_actuators, gripper_actuators, limits = panda_handles(model)
    before = tuple(float(data.qpos[address]) for address in qpos_addresses)

    renderer = mujoco.Renderer(model, height=256, width=256)
    renderer.update_scene(data, camera=make_camera(azimuth=140, elevation=-25, distance=2.0))
    exterior = renderer.render().copy()
    renderer.update_scene(data, camera=make_camera(azimuth=30, elevation=-10, distance=0.65))
    wrist = renderer.render().copy()
    observation = DroidObservation(
        make_frame(exterior), make_frame(wrist), DroidRobotState(before, 0.5),
        "Move the Panda end effector safely in simulation.",
    )

    transport = ProcessOwnedTransport(
        OpenPIWebsocketTransportFactory("127.0.0.1", 8000),
        request_timeout_seconds=5.0,
        startup_timeout_seconds=10.0,
    )
    policy = OfficialOpenPIDroidClient(transport, timeout_seconds=5.0, transport_is_thread_confined=True)
    report: dict[str, object] = {
        "scope": "one live pi05_droid request with synthetic Panda free-camera proxies; no task-success or transfer claim",
        "executed_action_count": 0,
        "safe_hold": False,
        "before_joint_positions": before,
    }
    try:
        started = perf_counter()
        response = policy.infer(observation)
        report["client_round_trip_ms"] = (perf_counter() - started) * 1000
        report["server_infer_ms"] = response.server_infer_ms
        report["policy_infer_ms"] = response.policy_infer_ms
        report["response_horizon"] = response.action_chunk.horizon
        action = response.action_chunk.actions[0]
        command = DroidLikePandaActionBridge(limits).to_position_command(
            current_joint_positions=before, droid_like_action=action
        )
        for actuator, target in zip(arm_actuators, command.joint_position_targets, strict=True):
            data.ctrl[actuator] = target
        for actuator in gripper_actuators:
            low, high = (float(value) for value in model.actuator_ctrlrange[actuator])
            data.ctrl[actuator] = low + command.gripper_normalized * (high - low)
        for _ in range(15):
            mujoco.mj_step(model, data)
        report.update(
            {
                "executed_action_count": 1,
                "first_policy_action": action,
                "bridge_clipped": command.clipped,
                "position_targets": command.joint_position_targets,
                "after_joint_positions": tuple(float(data.qpos[address]) for address in qpos_addresses),
            }
        )
    except Exception as error:
        report.update({"safe_hold": True, "safe_hold_reason": f"{type(error).__name__}: {error}"})
    finally:
        transport.close(force=True)
    (RESULT_ROOT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
