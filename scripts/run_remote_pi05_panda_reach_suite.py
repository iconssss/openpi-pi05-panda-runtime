"""Evaluate the π0.5/Panda bridge on a small, geometrically prechecked reach suite.

This is a systems-path experiment. Synthetic camera proxies and DROID-to-Panda
action mapping mean that outcome must not be presented as policy transfer skill.
"""

from __future__ import annotations

import json
from math import ceil
from pathlib import Path
from statistics import mean
from time import perf_counter

import mujoco
import numpy as np

from openpi_robot_runtime.observation_builder import DroidObservation, DroidRobotState, RGBFrame
from openpi_robot_runtime.official_openpi import OfficialOpenPIDroidClient
from openpi_robot_runtime.panda_bridge import DroidLikePandaActionBridge
from openpi_robot_runtime.panda_task import ReachMetric
from openpi_robot_runtime.remote_client import OpenPIWebsocketTransportFactory, ProcessOwnedTransport


TASK_XML = Path(
    "/root/shared-nvme/openpi-robot-runtime/assets/panda_menagerie/franka_emika_panda/project02_reach_task.xml"
)
RESULT_ROOT = Path("/root/shared-nvme/openpi-robot-runtime/results/pi05_panda_reach_suite")
TARGET_OFFSETS = (
    (0.12, -0.08, 0.04),
    (0.10, -0.06, 0.05),
    (0.13, -0.05, 0.03),
    (0.08, -0.10, 0.04),
    (0.11, -0.09, 0.02),
)
REPLANS_PER_TARGET = 40
PROMPT = "Move the Panda end effector to the green target safely in simulation."


def as_frame(image: np.ndarray) -> RGBFrame:
    rows = np.linspace(0, image.shape[0] - 1, 224).astype(np.intp)
    columns = np.linspace(0, image.shape[1] - 1, 224).astype(np.intp)
    return RGBFrame(224, 224, image[rows][:, columns, :3].astype(np.uint8, copy=False).tobytes())


def camera(azimuth: float, elevation: float, distance: float) -> mujoco.MjvCamera:
    value = mujoco.MjvCamera()
    value.type = mujoco.mjtCamera.mjCAMERA_FREE
    value.azimuth, value.elevation, value.distance = azimuth, elevation, distance
    value.lookat[:] = (0.0, 0.0, 0.45)
    return value


def handles(model: mujoco.MjModel) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...], tuple[int, ...], tuple[tuple[float, float], ...], int, int]:
    joint_ids = tuple(mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, f"joint{i}") for i in range(1, 8))
    qpos_addresses = tuple(int(model.jnt_qposadr[identifier]) for identifier in joint_ids)
    dof_addresses = tuple(int(model.jnt_dofadr[identifier]) for identifier in joint_ids)
    actuator_joint_ids = tuple(int(model.actuator_trnid[index, 0]) for index in range(model.nu))
    arm_actuators = tuple(actuator_joint_ids.index(identifier) for identifier in joint_ids)
    gripper_actuators = tuple(index for index in range(model.nu) if index not in arm_actuators)
    hand_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "hand")
    target_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "reach_target")
    if any(identifier < 0 for identifier in (*joint_ids, hand_id, target_id)) or not gripper_actuators:
        raise RuntimeError("Task scene did not resolve the Panda reach interfaces.")
    limits = tuple(tuple(float(value) for value in model.jnt_range[identifier]) for identifier in joint_ids)
    return qpos_addresses, dof_addresses, arm_actuators, gripper_actuators, limits, hand_id, target_id


def reset(model: mujoco.MjModel, data: mujoco.MjData, hand_id: int, target_id: int, offset: tuple[float, float, float]) -> ReachMetric:
    key_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "home")
    mujoco.mj_resetDataKeyframe(model, data, key_id)
    mujoco.mj_forward(model, data)
    target = data.xpos[hand_id].copy() + np.asarray(offset)
    mocap_id = int(model.body_mocapid[target_id])
    data.mocap_pos[mocap_id] = target
    mujoco.mj_forward(model, data)
    return ReachMetric(tuple(float(value) for value in target))


def ik_residual(
    model: mujoco.MjModel,
    hand_id: int,
    target: tuple[float, float, float],
    qpos_addresses: tuple[int, ...],
    dof_addresses: tuple[int, ...],
    limits: tuple[tuple[float, float], ...],
) -> float:
    candidate = mujoco.MjData(model)
    key_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "home")
    mujoco.mj_resetDataKeyframe(model, candidate, key_id)
    mujoco.mj_forward(model, candidate)
    for _ in range(120):
        error = np.asarray(target) - candidate.xpos[hand_id]
        if float(np.linalg.norm(error)) <= 0.002:
            break
        jacp, jacr = np.zeros((3, model.nv)), np.zeros((3, model.nv))
        mujoco.mj_jacBody(model, candidate, jacp, jacr, hand_id)
        reduced = jacp[:, dof_addresses]
        update = reduced.T @ np.linalg.solve(reduced @ reduced.T + 1e-4 * np.eye(3), error)
        for address, delta, (lower, upper) in zip(qpos_addresses, np.clip(update, -0.08, 0.08), limits, strict=True):
            candidate.qpos[address] = np.clip(candidate.qpos[address] + delta, lower, upper)
        mujoco.mj_forward(model, candidate)
    return float(np.linalg.norm(np.asarray(target) - candidate.xpos[hand_id]))


def p95(values: list[float]) -> float | None:
    return sorted(values)[min(len(values) - 1, ceil(0.95 * len(values)) - 1)] if values else None


def main() -> None:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    model = mujoco.MjModel.from_xml_path(str(TASK_XML))
    data = mujoco.MjData(model)
    qpos_addresses, dof_addresses, arm_actuators, gripper_actuators, limits, hand_id, target_id = handles(model)
    bridge = DroidLikePandaActionBridge(limits)
    physics_steps = max(1, round(bridge.control_dt_seconds / model.opt.timestep))
    renderer = mujoco.Renderer(model, height=256, width=256)
    exterior_camera, wrist_camera = camera(140, -25, 2.0), camera(30, -10, 0.65)
    transport = ProcessOwnedTransport(OpenPIWebsocketTransportFactory("127.0.0.1", 8000), request_timeout_seconds=5.0, startup_timeout_seconds=10.0)
    policy = OfficialOpenPIDroidClient(transport, timeout_seconds=5.0, transport_is_thread_confined=True)
    episodes: list[dict[str, object]] = []
    try:
        for index, offset in enumerate(TARGET_OFFSETS):
            metric = reset(model, data, hand_id, target_id, offset)
            oracle_residual = ik_residual(model, hand_id, metric.target_position, qpos_addresses, dof_addresses, limits)
            initial_distance = metric.distance_meters(tuple(float(value) for value in data.xpos[hand_id]))
            rtts: list[float] = []
            clipped = 0
            safe_hold: str | None = None
            for step in range(REPLANS_PER_TARGET):
                current = tuple(float(data.qpos[address]) for address in qpos_addresses)
                renderer.update_scene(data, camera=exterior_camera)
                exterior = renderer.render().copy()
                renderer.update_scene(data, camera=wrist_camera)
                wrist = renderer.render().copy()
                if step == 0:
                    iio_path = RESULT_ROOT / f"target_{index}_initial.png"
                    import imageio.v3 as iio
                    iio.imwrite(iio_path, exterior)
                try:
                    started = perf_counter()
                    response = policy.infer(DroidObservation(as_frame(exterior), as_frame(wrist), DroidRobotState(current, 0.5), PROMPT))
                    rtts.append((perf_counter() - started) * 1000)
                    command = bridge.to_position_command(current_joint_positions=current, droid_like_action=response.action_chunk.actions[0])
                    for actuator, target in zip(arm_actuators, command.joint_position_targets, strict=True):
                        data.ctrl[actuator] = target
                    for actuator in gripper_actuators:
                        lower, upper = (float(value) for value in model.actuator_ctrlrange[actuator])
                        data.ctrl[actuator] = lower + command.gripper_normalized * (upper - lower)
                    for _ in range(physics_steps):
                        mujoco.mj_step(model, data)
                    clipped += int(command.clipped)
                except Exception as error:
                    safe_hold = f"{type(error).__name__}: {error}"
                    break
            final_hand = tuple(float(value) for value in data.xpos[hand_id])
            episodes.append(
                {
                    "target_index": index,
                    "target_offset_m": offset,
                    "ik_oracle_residual_m": oracle_residual,
                    "initial_distance_m": initial_distance,
                    "final_distance_m": metric.distance_meters(final_hand),
                    "success_threshold_m": metric.threshold_meters,
                    "success": metric.success(final_hand),
                    "completed_replans": len(rtts),
                    "safe_hold": safe_hold,
                    "bridge_clipped_replans": clipped,
                    "client_rtt_mean_ms": mean(rtts) if rtts else None,
                    "client_rtt_p95_ms": p95(rtts),
                }
            )
    finally:
        transport.close(force=True)
    report = {
        "scope": "five-target synthetic Panda reach suite through live pi05_droid, process-owned deadline, and first-action bridge; no transfer/task-performance claim",
        "requested_replans": len(TARGET_OFFSETS) * REPLANS_PER_TARGET,
        "completed_replans": sum(int(episode["completed_replans"]) for episode in episodes),
        "successful_episodes": sum(bool(episode["success"]) for episode in episodes),
        "safe_hold_episodes": sum(episode["safe_hold"] is not None for episode in episodes),
        "episodes": episodes,
    }
    (RESULT_ROOT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
