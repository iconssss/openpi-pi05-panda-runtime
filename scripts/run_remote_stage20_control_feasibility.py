"""CPU-only Stage 20 Panda bridge feasibility ladder; no pi05 dependency."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

import mujoco
import numpy as np

from openpi_robot_runtime.panda_bridge import DroidLikePandaActionBridge
from openpi_robot_runtime.panda_task import ReachMetric
from openpi_robot_runtime.stage20 import (
    DIAGNOSTIC_TARGETS, DLS_DIAGNOSTIC_CONDITIONS, FINAL_TEST_TARGETS,
    FIXED_RAW_ACTION, select_diagnostic_condition,
)


TASK_XML = Path("/root/shared-nvme/openpi-robot-runtime/assets/panda_menagerie/franka_emika_panda/project02_reach_task.xml")
RESULT_ROOT = Path("/root/shared-nvme/openpi-robot-runtime/results/stage20_control_feasibility")
DIRECT_IK_STEPS = 120


def handles(model: mujoco.MjModel) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...], tuple[int, ...], tuple[tuple[float, float], ...], int, int]:
    joint_ids = tuple(mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, f"joint{i}") for i in range(1, 8))
    qpos = tuple(int(model.jnt_qposadr[joint]) for joint in joint_ids)
    dof = tuple(int(model.jnt_dofadr[joint]) for joint in joint_ids)
    actuator_joints = tuple(int(model.actuator_trnid[index, 0]) for index in range(model.nu))
    arm = tuple(actuator_joints.index(joint) for joint in joint_ids)
    gripper = tuple(index for index in range(model.nu) if index not in arm)
    hand = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "hand")
    target = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "reach_target")
    if any(value < 0 for value in (*joint_ids, hand, target)) or not gripper:
        raise RuntimeError("Panda reach interfaces unavailable.")
    return qpos, dof, arm, gripper, tuple(tuple(float(value) for value in model.jnt_range[joint]) for joint in joint_ids), hand, target


def reset(model: mujoco.MjModel, data: mujoco.MjData, hand_id: int, target_id: int, offset: tuple[float, float, float]) -> ReachMetric:
    mujoco.mj_resetDataKeyframe(model, data, mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "home"))
    mujoco.mj_forward(model, data)
    target = data.xpos[hand_id].copy() + np.asarray(offset)
    data.mocap_pos[int(model.body_mocapid[target_id])] = target
    mujoco.mj_forward(model, data)
    return ReachMetric(tuple(float(value) for value in target))


def dls_velocity(model: mujoco.MjModel, data: mujoco.MjData, hand_id: int, dof: tuple[int, ...], target: tuple[float, float, float]) -> tuple[float, ...]:
    error = np.asarray(target) - data.xpos[hand_id]
    jacobian, rotation = np.zeros((3, model.nv)), np.zeros((3, model.nv))
    mujoco.mj_jacBody(model, data, jacobian, rotation, hand_id)
    reduced = jacobian[:, dof]
    return tuple(float(value) for value in np.clip(reduced.T @ np.linalg.solve(reduced @ reduced.T + 1e-4 * np.eye(3), error), -1.0, 1.0))


def step_bridge(model: mujoco.MjModel, data: mujoco.MjData, bridge: DroidLikePandaActionBridge, action: tuple[float, ...], qpos: tuple[int, ...], arm: tuple[int, ...], gripper: tuple[int, ...]) -> bool:
    command = bridge.to_position_command(current_joint_positions=tuple(float(data.qpos[address]) for address in qpos), droid_like_action=action)
    for actuator, target in zip(arm, command.joint_position_targets, strict=True):
        data.ctrl[actuator] = target
    for actuator in gripper:
        lower, upper = (float(value) for value in model.actuator_ctrlrange[actuator])
        data.ctrl[actuator] = lower + command.gripper_normalized * (upper - lower)
    for _ in range(max(1, round(bridge.control_dt_seconds / model.opt.timestep))):
        mujoco.mj_step(model, data)
    return command.clipped


def solve_direct_ik(model: mujoco.MjModel, data: mujoco.MjData, hand_id: int, target: tuple[float, float, float], qpos: tuple[int, ...], dof: tuple[int, ...], limits: tuple[tuple[float, float], ...]) -> tuple[float, ...]:
    for _ in range(120):
        error = np.asarray(target) - data.xpos[hand_id]
        if float(np.linalg.norm(error)) <= 0.002:
            break
        jacobian, rotation = np.zeros((3, model.nv)), np.zeros((3, model.nv))
        mujoco.mj_jacBody(model, data, jacobian, rotation, hand_id)
        update = jacobian[:, dof].T @ np.linalg.solve(jacobian[:, dof] @ jacobian[:, dof].T + 1e-4 * np.eye(3), error)
        for address, delta, limit in zip(qpos, np.clip(update, -0.08, 0.08), limits, strict=True):
            data.qpos[address] = np.clip(data.qpos[address] + delta, *limit)
        mujoco.mj_forward(model, data)
    return tuple(float(data.qpos[address]) for address in qpos)


def execute_episode(model: mujoco.MjModel, data: mujoco.MjData, *, split: str, target_index: int, offset: tuple[float, float, float], controller: str, bridge_dt_seconds: float, steps: int, interfaces: tuple[object, ...]) -> dict[str, object]:
    qpos, dof, arm, gripper, limits, hand_id, target_id = interfaces
    metric = reset(model, data, hand_id, target_id, offset)
    initial = metric.distance_meters(tuple(float(value) for value in data.xpos[hand_id]))
    curve = [initial]
    clips = 0
    safety_event: str | None = None
    completed = 0
    try:
        if controller == "direct_position_ik_oracle":
            solution = solve_direct_ik(model, data, hand_id, metric.target_position, qpos, dof, limits)
            metric = reset(model, data, hand_id, target_id, offset)
            curve = [metric.distance_meters(tuple(float(value) for value in data.xpos[hand_id]))]
            for _ in range(steps):
                for actuator, target in zip(arm, solution, strict=True):
                    data.ctrl[actuator] = target
                for actuator in gripper:
                    data.ctrl[actuator] = float(model.actuator_ctrlrange[actuator, 1])
                for _ in range(33):
                    mujoco.mj_step(model, data)
                completed += 1
                curve.append(metric.distance_meters(tuple(float(value) for value in data.xpos[hand_id])))
                if metric.success(tuple(float(value) for value in data.xpos[hand_id])):
                    break
        else:
            bridge = DroidLikePandaActionBridge(limits, control_dt_seconds=bridge_dt_seconds)
            for _ in range(steps):
                if controller == "no_op":
                    mujoco.mj_step(model, data)
                else:
                    action = FIXED_RAW_ACTION if controller == "fixed_raw_action_bridge" else dls_velocity(model, data, hand_id, dof, metric.target_position) + (0.5,)
                    clips += int(step_bridge(model, data, bridge, action, qpos, arm, gripper))
                completed += 1
                curve.append(metric.distance_meters(tuple(float(value) for value in data.xpos[hand_id])))
                if metric.success(tuple(float(value) for value in data.xpos[hand_id])):
                    break
    except Exception as error:
        safety_event = f"{type(error).__name__}: {error}"
    return {"split": split, "target_index": target_index, "target_offset_m": offset, "controller": controller, "bridge_dt_seconds": bridge_dt_seconds, "requested_steps": steps, "completed_steps": completed, "distance_curve_m": curve, "initial_distance_m": curve[0], "final_distance_m": curve[-1], "success_threshold_m": metric.threshold_meters, "success": metric.success(tuple(float(value) for value in data.xpos[hand_id])) if safety_event is None else False, "bridge_clipped_steps": clips, "safety_event": safety_event}


def summarize(rows: list[dict[str, object]]) -> dict[str, object]:
    return {"episodes": len(rows), "successes": sum(bool(row["success"]) for row in rows), "safety_events": sum(row["safety_event"] is not None for row in rows), "bridge_clipped_steps": sum(int(row["bridge_clipped_steps"]) for row in rows), "mean_final_distance_m": mean(float(row["final_distance_m"]) for row in rows)}


def main() -> None:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    model, data = mujoco.MjModel.from_xml_path(str(TASK_XML)), None
    data = mujoco.MjData(model)
    interfaces = handles(model)
    diagnostic: list[dict[str, object]] = []
    for condition in DLS_DIAGNOSTIC_CONDITIONS:
        for index, offset in enumerate(DIAGNOSTIC_TARGETS):
            episode = execute_episode(model, data, split="diagnostic", target_index=index, offset=offset, controller="closed_loop_dls_velocity_oracle", bridge_dt_seconds=condition.bridge_dt_seconds, steps=condition.episode_steps, interfaces=interfaces)
            episode["condition"] = condition.name
            diagnostic.append(episode)
    selected = select_diagnostic_condition(diagnostic)
    condition = next(value for value in DLS_DIAGNOSTIC_CONDITIONS if value.name == selected)
    final: list[dict[str, object]] = []
    for index, offset in enumerate(FINAL_TEST_TARGETS):
        final.extend((
            execute_episode(model, data, split="final_test", target_index=index, offset=offset, controller="no_op", bridge_dt_seconds=condition.bridge_dt_seconds, steps=condition.episode_steps, interfaces=interfaces),
            execute_episode(model, data, split="final_test", target_index=index, offset=offset, controller="fixed_raw_action_bridge", bridge_dt_seconds=condition.bridge_dt_seconds, steps=condition.episode_steps, interfaces=interfaces),
            execute_episode(model, data, split="final_test", target_index=index, offset=offset, controller="closed_loop_dls_velocity_oracle", bridge_dt_seconds=condition.bridge_dt_seconds, steps=condition.episode_steps, interfaces=interfaces),
            execute_episode(model, data, split="final_test", target_index=index, offset=offset, controller="direct_position_ik_oracle", bridge_dt_seconds=0.0, steps=DIRECT_IK_STEPS, interfaces=interfaces),
        ))
    grouped = {name: summarize([row for row in final if row["controller"] == name]) for name in ("no_op", "fixed_raw_action_bridge", "closed_loop_dls_velocity_oracle", "direct_position_ik_oracle")}
    report = {"scope": "Stage 20 CPU-only Panda control feasibility ladder; no pi05 server, request, adapter, or training", "protocol": {"diagnostic_targets": DIAGNOSTIC_TARGETS, "final_test_targets": FINAL_TEST_TARGETS, "dls_conditions": [value.__dict__ for value in DLS_DIAGNOSTIC_CONDITIONS], "selected_diagnostic_condition": selected}, "diagnostic": diagnostic, "final_test": final, "final_summary": grouped}
    (RESULT_ROOT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"selected_diagnostic_condition": selected, "final_summary": grouped}, indent=2))


if __name__ == "__main__":
    main()
