"""Validate the controlled reach task using no-op and bounded-random baselines.

No π0.5 policy is loaded or queried.  This establishes an independent task
metric before any later bridge-path comparison is considered.
"""

from __future__ import annotations

import json
from pathlib import Path

import imageio.v3 as iio
import mujoco
import numpy as np

from openpi_robot_runtime.panda_bridge import DroidLikePandaActionBridge
from openpi_robot_runtime.panda_task import ReachMetric


TASK_XML = Path(
    "/root/shared-nvme/openpi-robot-runtime/assets/panda_menagerie/franka_emika_panda/project02_reach_task.xml"
)
RESULT_ROOT = Path("/root/shared-nvme/openpi-robot-runtime/results/panda_reach_baselines")
TARGET_OFFSET = np.array((0.12, -0.08, 0.04), dtype=np.float64)
CONTROL_CYCLES = 30


def handles(model: mujoco.MjModel) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...], tuple[int, ...], tuple[tuple[float, float], ...], int, int]:
    joint_ids = tuple(mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, f"joint{i}") for i in range(1, 8))
    if any(identifier < 0 for identifier in joint_ids):
        raise RuntimeError("Expected Panda joint1..joint7 are unavailable.")
    qpos_addresses = tuple(int(model.jnt_qposadr[identifier]) for identifier in joint_ids)
    dof_addresses = tuple(int(model.jnt_dofadr[identifier]) for identifier in joint_ids)
    transmission_ids = tuple(int(model.actuator_trnid[index, 0]) for index in range(model.nu))
    arm_actuators = tuple(transmission_ids.index(identifier) for identifier in joint_ids)
    gripper_actuators = tuple(index for index in range(model.nu) if index not in arm_actuators)
    hand_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "hand")
    target_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "reach_target")
    if hand_id < 0 or target_id < 0 or not gripper_actuators:
        raise RuntimeError("Task scene did not resolve hand, target, or gripper.")
    limits = tuple(tuple(float(value) for value in model.jnt_range[identifier]) for identifier in joint_ids)
    return qpos_addresses, dof_addresses, arm_actuators, gripper_actuators, limits, hand_id, target_id


def reset_task(model: mujoco.MjModel, data: mujoco.MjData, hand_id: int, target_id: int) -> ReachMetric:
    key_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "home")
    if key_id < 0:
        raise RuntimeError("Official Panda home keyframe is missing.")
    mujoco.mj_resetDataKeyframe(model, data, key_id)
    mujoco.mj_forward(model, data)
    target = data.xpos[hand_id].copy() + TARGET_OFFSET
    mocap_id = int(model.body_mocapid[target_id])
    if mocap_id < 0:
        raise RuntimeError("Reach target must be a mocap body.")
    data.mocap_pos[mocap_id] = target
    mujoco.mj_forward(model, data)
    return ReachMetric(tuple(float(value) for value in target))


def execute_action(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    bridge: DroidLikePandaActionBridge,
    action: tuple[float, ...],
    qpos_addresses: tuple[int, ...],
    arm_actuators: tuple[int, ...],
    gripper_actuators: tuple[int, ...],
) -> bool:
    current = tuple(float(data.qpos[address]) for address in qpos_addresses)
    command = bridge.to_position_command(current_joint_positions=current, droid_like_action=action)
    for actuator, target in zip(arm_actuators, command.joint_position_targets, strict=True):
        data.ctrl[actuator] = target
    for actuator in gripper_actuators:
        lower, upper = (float(value) for value in model.actuator_ctrlrange[actuator])
        data.ctrl[actuator] = lower + command.gripper_normalized * (upper - lower)
    for _ in range(max(1, round(bridge.control_dt_seconds / model.opt.timestep))):
        mujoco.mj_step(model, data)
    return command.clipped


def solve_reach_ik(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    hand_id: int,
    target: tuple[float, float, float],
    qpos_addresses: tuple[int, ...],
    dof_addresses: tuple[int, ...],
    limits: tuple[tuple[float, float], ...],
) -> tuple[tuple[float, ...], float]:
    """Small DLS position IK oracle used only to validate task solvability."""
    for _ in range(120):
        hand = data.xpos[hand_id].copy()
        error = np.asarray(target) - hand
        if float(np.linalg.norm(error)) <= 0.002:
            break
        jacobian_position = np.zeros((3, model.nv))
        jacobian_rotation = np.zeros((3, model.nv))
        mujoco.mj_jacBody(model, data, jacobian_position, jacobian_rotation, hand_id)
        reduced = jacobian_position[:, dof_addresses]
        step = reduced.T @ np.linalg.solve(reduced @ reduced.T + 1e-4 * np.eye(3), error)
        step = np.clip(step, -0.08, 0.08)
        for address, delta, (lower, upper) in zip(qpos_addresses, step, limits, strict=True):
            data.qpos[address] = np.clip(data.qpos[address] + delta, lower, upper)
        mujoco.mj_forward(model, data)
    solution = tuple(float(data.qpos[address]) for address in qpos_addresses)
    residual = float(np.linalg.norm(np.asarray(target) - data.xpos[hand_id]))
    return solution, residual


def execute_position_hold(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    arm_actuators: tuple[int, ...],
    gripper_actuators: tuple[int, ...],
    arm_targets: tuple[float, ...],
) -> None:
    for actuator, target in zip(arm_actuators, arm_targets, strict=True):
        data.ctrl[actuator] = target
    for actuator in gripper_actuators:
        data.ctrl[actuator] = 255.0
    for _ in range(33):
        mujoco.mj_step(model, data)


def main() -> None:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    model = mujoco.MjModel.from_xml_path(str(TASK_XML))
    data = mujoco.MjData(model)
    qpos_addresses, dof_addresses, arm_actuators, gripper_actuators, limits, hand_id, target_id = handles(model)
    bridge = DroidLikePandaActionBridge(limits)
    renderer = mujoco.Renderer(model, height=384, width=512)
    results: list[dict[str, object]] = []
    for name, rng in (("zero_droid_like_action", None), ("bounded_random_seed_7", np.random.default_rng(7))):
        metric = reset_task(model, data, hand_id, target_id)
        initial_distance = metric.distance_meters(tuple(float(value) for value in data.xpos[hand_id]))
        clipped = 0
        for _ in range(CONTROL_CYCLES):
            action = (0.0,) * 8 if rng is None else tuple(float(value) for value in rng.uniform(-0.25, 0.25, size=7)) + (0.5,)
            clipped += int(execute_action(model, data, bridge, action, qpos_addresses, arm_actuators, gripper_actuators))
        final_hand = tuple(float(value) for value in data.xpos[hand_id])
        final_distance = metric.distance_meters(final_hand)
        renderer.update_scene(data, camera=-1)
        image_path = RESULT_ROOT / f"{name}.png"
        iio.imwrite(image_path, renderer.render())
        results.append(
            {
                "baseline": name,
                "control_cycles": CONTROL_CYCLES,
                "initial_distance_m": initial_distance,
                "final_distance_m": final_distance,
                "success_threshold_m": metric.threshold_meters,
                "success": metric.success(final_hand),
                "bridge_clipped_cycles": clipped,
                "image_artifact": str(image_path),
            }
        )
    metric = reset_task(model, data, hand_id, target_id)
    solution, ik_residual = solve_reach_ik(
        model, data, hand_id, metric.target_position, qpos_addresses, dof_addresses, limits
    )
    # Return to the same task reset before using the oracle joint target through
    # the model's ordinary position actuators.
    metric = reset_task(model, data, hand_id, target_id)
    for _ in range(120):
        execute_position_hold(model, data, arm_actuators, gripper_actuators, solution)
        final_hand = tuple(float(value) for value in data.xpos[hand_id])
        if metric.success(final_hand):
            break
    final_hand = tuple(float(value) for value in data.xpos[hand_id])
    renderer.update_scene(data, camera=-1)
    oracle_image = RESULT_ROOT / "dls_ik_oracle.png"
    iio.imwrite(oracle_image, renderer.render())
    results.append(
        {
            "baseline": "dls_ik_oracle_not_learned_policy",
            "control_cycles": 120,
            "ik_solution_residual_m": ik_residual,
            "final_distance_m": metric.distance_meters(final_hand),
            "success_threshold_m": metric.threshold_meters,
            "success": metric.success(final_hand),
            "image_artifact": str(oracle_image),
        }
    )
    report = {
        "scope": "controlled Panda geometric reach task validation with zero-action, deterministic bounded-random, and non-learned DLS IK oracle baselines; no OpenPI policy call",
        "target_offset_from_home_hand_m": TARGET_OFFSET.tolist(),
        "task_metric": "Euclidean distance from Panda hand body origin to independent static mocap target <= 0.04 m",
        "baselines": results,
    }
    (RESULT_ROOT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
