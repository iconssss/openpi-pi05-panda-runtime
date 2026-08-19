"""CPU-only Stage 20B DLS contract replication; no pi05 or adapter dependency."""
from __future__ import annotations
import json
from pathlib import Path
from statistics import mean
import mujoco
import numpy as np

from openpi_robot_runtime.panda_bridge import DroidLikePandaActionBridge
from openpi_robot_runtime.stage20 import FIXED_RAW_ACTION
from openpi_robot_runtime.stage20b import CONDITIONS, DEVELOPMENT_TARGETS, FINAL_TEST_TARGETS, TARGET_SEED, ContractCondition, select_condition
from run_remote_stage20_control_feasibility import handles, reset, solve_direct_ik, step_bridge

TASK_XML = Path("/root/shared-nvme/openpi-robot-runtime/assets/panda_menagerie/franka_emika_panda/project02_reach_task.xml")
RESULT_ROOT = Path("/root/shared-nvme/openpi-robot-runtime/results/stage20b_control_contract")
DIRECT_IK_STEPS = 120

def teacher(model: mujoco.MjModel, data: mujoco.MjData, hand_id: int, dof: tuple[int, ...], target: tuple[float, float, float], condition: ContractCondition) -> tuple[float, ...]:
    error = np.asarray(target) - data.xpos[hand_id]; magnitude = float(np.linalg.norm(error))
    jac, rot = np.zeros((3, model.nv)), np.zeros((3, model.nv)); mujoco.mj_jacBody(model, data, jac, rot, hand_id)
    reduced = jac[:, dof]
    velocity = reduced.T @ np.linalg.solve(reduced @ reduced.T + condition.damping**2 * np.eye(3), error)
    if condition.slowdown_radius_m is not None: velocity *= min(1.0, magnitude / condition.slowdown_radius_m)
    return tuple(float(value) for value in velocity) + (0.5,)

def ik_residual(model: mujoco.MjModel, interfaces: tuple[object, ...], offset: tuple[float, float, float]) -> float:
    scratch = mujoco.MjData(model); qpos, dof, arm, gripper, limits, hand, target_id = interfaces
    metric = reset(model, scratch, hand, target_id, offset); solve_direct_ik(model, scratch, hand, metric.target_position, qpos, dof, limits)
    return metric.distance_meters(tuple(float(value) for value in scratch.xpos[hand]))

def episode(model: mujoco.MjModel, data: mujoco.MjData, interfaces: tuple[object, ...], split: str, target_index: int, offset: tuple[float, float, float], controller: str, condition: ContractCondition | None, steps: int) -> dict[str, object]:
    qpos, dof, arm, gripper, limits, hand, target_id = interfaces; metric = reset(model, data, hand, target_id, offset)
    residual = ik_residual(model, interfaces, offset); curve = [metric.distance_meters(tuple(float(value) for value in data.xpos[hand]))]; clips = completed = 0; event = None
    try:
        if controller == "direct_position_ik_oracle":
            solution = solve_direct_ik(model, data, hand, metric.target_position, qpos, dof, limits); metric = reset(model, data, hand, target_id, offset); curve = [metric.distance_meters(tuple(float(value) for value in data.xpos[hand]))]
            for _ in range(steps):
                for actuator, value in zip(arm, solution, strict=True): data.ctrl[actuator] = value
                for actuator in gripper: data.ctrl[actuator] = float(model.actuator_ctrlrange[actuator, 1])
                for _ in range(33): mujoco.mj_step(model, data)
                completed += 1; curve.append(metric.distance_meters(tuple(float(value) for value in data.xpos[hand])))
                if metric.success(tuple(float(value) for value in data.xpos[hand])): break
        else:
            bridge = DroidLikePandaActionBridge(limits, control_dt_seconds=condition.control_dt_seconds if condition else 0.20, max_joint_velocity=condition.max_joint_velocity if condition else 1.0)
            for _ in range(steps):
                if controller == "no_op": mujoco.mj_step(model, data)
                else:
                    action = FIXED_RAW_ACTION if controller == "fixed_raw_action_bridge" else teacher(model, data, hand, dof, metric.target_position, condition)
                    clips += int(step_bridge(model, data, bridge, action, qpos, arm, gripper))
                completed += 1; curve.append(metric.distance_meters(tuple(float(value) for value in data.xpos[hand])))
                if metric.success(tuple(float(value) for value in data.xpos[hand])): break
    except Exception as error: event = f"{type(error).__name__}: {error}"
    return {"split": split, "target_index": target_index, "target_offset_m": offset, "controller": controller, "condition": condition.name if condition else None, "ik_residual_m": residual, "requested_steps": steps, "completed_steps": completed, "distance_curve_m": curve, "initial_distance_m": curve[0], "final_distance_m": curve[-1], "success_threshold_m": metric.threshold_meters, "success": event is None and metric.success(tuple(float(value) for value in data.xpos[hand])), "bridge_clipped_steps": clips, "safety_event": event}

def summary(rows: list[dict[str, object]]) -> dict[str, object]:
    return {"episodes": len(rows), "successes": sum(bool(row["success"]) for row in rows), "mean_final_distance_m": mean(float(row["final_distance_m"]) for row in rows), "bridge_clipped_steps": sum(int(row["bridge_clipped_steps"]) for row in rows), "safety_events": sum(row["safety_event"] is not None for row in rows)}

def main() -> None:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True); model = mujoco.MjModel.from_xml_path(str(TASK_XML)); data = mujoco.MjData(model); interfaces = handles(model)
    development = []
    for condition in CONDITIONS:
        for index, offset in enumerate(DEVELOPMENT_TARGETS): development.append(episode(model, data, interfaces, "development", index, offset, "closed_loop_dls_velocity_oracle", condition, condition.episode_steps))
    selected_name = select_condition(development); selected = next(item for item in CONDITIONS if item.name == selected_name)
    final = []
    for index, offset in enumerate(FINAL_TEST_TARGETS):
        final.extend((episode(model, data, interfaces, "final_test", index, offset, "no_op", selected, selected.episode_steps), episode(model, data, interfaces, "final_test", index, offset, "fixed_raw_action_bridge", selected, selected.episode_steps), episode(model, data, interfaces, "final_test", index, offset, "closed_loop_dls_velocity_oracle", selected, selected.episode_steps), episode(model, data, interfaces, "final_test", index, offset, "direct_position_ik_oracle", None, DIRECT_IK_STEPS)))
    names = ("no_op", "fixed_raw_action_bridge", "closed_loop_dls_velocity_oracle", "direct_position_ik_oracle"); report = {"scope": "Stage 20B CPU-only low-level DLS contract replication; no pi05 server, GPU inference, adapter, or training", "target_seed": TARGET_SEED, "development": development, "selected_condition": selected.__dict__, "final_test": final, "final_summary": {name: summary([row for row in final if row["controller"] == name]) for name in names}}
    (RESULT_ROOT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8"); print(json.dumps({"selected_condition": selected.__dict__, "final_summary": report["final_summary"]}, indent=2))

if __name__ == "__main__": main()
