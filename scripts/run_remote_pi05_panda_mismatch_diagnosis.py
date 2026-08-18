"""Stage 17: pre-registered diagnosis of DROID-to-Panda embodiment mismatch.

The experiment does not train, tune, or select an action map.  It evaluates
fixed visual conditions and three explicitly declared action interpretations.
Targets 0--7 are diagnostic; targets 8--11 are held out and must never be used
to choose a future adapter.  Each live policy response is used only for a
single MuJoCo action, so failures are directly attributable to the immediate
observation/action convention rather than long-horizon compounding.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from time import perf_counter

import mujoco
import numpy as np

from openpi_robot_runtime.embodiment_diagnostics import ActionInterpretation, cosine_alignment, one_step_progress
from openpi_robot_runtime.observation_builder import DroidObservation, DroidRobotState, RGBFrame
from openpi_robot_runtime.official_openpi import OfficialOpenPIDroidClient
from openpi_robot_runtime.panda_bridge import DroidLikePandaActionBridge
from openpi_robot_runtime.panda_task import ReachMetric
from openpi_robot_runtime.remote_client import OpenPIWebsocketTransportFactory, ProcessOwnedTransport


TASK_XML = Path("/root/shared-nvme/openpi-robot-runtime/assets/panda_menagerie/franka_emika_panda/project02_reach_task.xml")
RESULT_ROOT = Path("/root/shared-nvme/openpi-robot-runtime/results/pi05_panda_mismatch_diagnosis")
PROMPT = "Move the Panda end effector to the green target safely in simulation."
TARGET_OFFSETS = (
    (0.08, -0.10, 0.02), (0.10, -0.06, 0.03), (0.10, -0.08, 0.05), (0.12, -0.08, 0.04),
    (0.13, -0.05, 0.03), (0.11, -0.09, 0.02), (0.09, -0.07, 0.05), (0.12, -0.06, 0.02),
    (0.08, -0.08, 0.03), (0.11, -0.05, 0.04), (0.13, -0.09, 0.02), (0.09, -0.10, 0.04),
)
DIAGNOSTIC_TARGET_COUNT = 8


@dataclass(frozen=True)
class VisualCondition:
    name: str
    exterior_azimuth: float
    exterior_elevation: float
    exterior_distance: float
    brightness_gain: float = 1.0
    noise_stddev: float = 0.0


VISUAL_CONDITIONS = (
    VisualCondition("canonical", 140.0, -25.0, 2.0),
    VisualCondition("exterior_left_25deg", 115.0, -25.0, 2.0),
    VisualCondition("exterior_right_25deg", 165.0, -25.0, 2.0),
    VisualCondition("exterior_high_15deg", 140.0, -10.0, 2.0),
    VisualCondition("dark_gain_0_65", 140.0, -25.0, 2.0, brightness_gain=0.65),
    VisualCondition("rgb_noise_stddev_12", 140.0, -25.0, 2.0, noise_stddev=12.0),
)
ACTION_INTERPRETATIONS = (
    ActionInterpretation("identity"),
    ActionInterpretation("global_arm_negation", arm_sign=-1.0),
    ActionInterpretation("identity_quarter_gain", arm_gain=0.25),
)


def as_frame(image: np.ndarray) -> RGBFrame:
    rows = np.linspace(0, image.shape[0] - 1, 224).astype(np.intp)
    columns = np.linspace(0, image.shape[1] - 1, 224).astype(np.intp)
    return RGBFrame(224, 224, image[rows][:, columns, :3].astype(np.uint8, copy=False).tobytes())


def free_camera(azimuth: float, elevation: float, distance: float) -> mujoco.MjvCamera:
    value = mujoco.MjvCamera()
    value.type = mujoco.mjtCamera.mjCAMERA_FREE
    value.azimuth, value.elevation, value.distance = azimuth, elevation, distance
    value.lookat[:] = (0.0, 0.0, 0.45)
    return value


def apply_visual_variant(image: np.ndarray, condition: VisualCondition, rng: np.random.Generator) -> np.ndarray:
    value = image.astype(np.float32) * condition.brightness_gain
    if condition.noise_stddev:
        value += rng.normal(0.0, condition.noise_stddev, size=value.shape)
    return np.clip(value, 0, 255).astype(np.uint8)


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
    data.mocap_pos[int(model.body_mocapid[target_id])] = target
    mujoco.mj_forward(model, data)
    return ReachMetric(tuple(float(value) for value in target))


def oracle_joint_direction(model: mujoco.MjModel, data: mujoco.MjData, hand_id: int, dof_addresses: tuple[int, ...], target: tuple[float, float, float]) -> tuple[float, ...]:
    error = np.asarray(target) - data.xpos[hand_id]
    jacobian_position, jacobian_rotation = np.zeros((3, model.nv)), np.zeros((3, model.nv))
    mujoco.mj_jacBody(model, data, jacobian_position, jacobian_rotation, hand_id)
    reduced = jacobian_position[:, dof_addresses]
    direction = reduced.T @ np.linalg.solve(reduced @ reduced.T + 1e-4 * np.eye(3), error)
    return tuple(float(value) for value in np.clip(direction, -1.0, 1.0))


def execute_one_action(model: mujoco.MjModel, data: mujoco.MjData, bridge: DroidLikePandaActionBridge, action: tuple[float, ...], qpos_addresses: tuple[int, ...], arm_actuators: tuple[int, ...], gripper_actuators: tuple[int, ...]) -> bool:
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


def main() -> None:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    model, data = mujoco.MjModel.from_xml_path(str(TASK_XML)), None
    data = mujoco.MjData(model)
    qpos_addresses, dof_addresses, arm_actuators, gripper_actuators, limits, hand_id, target_id = handles(model)
    bridge = DroidLikePandaActionBridge(limits)
    renderer = mujoco.Renderer(model, height=256, width=256)
    wrist_camera = free_camera(30.0, -10.0, 0.65)
    rng = np.random.default_rng(20260818)
    transport = ProcessOwnedTransport(OpenPIWebsocketTransportFactory("127.0.0.1", 8000), request_timeout_seconds=5.0, startup_timeout_seconds=10.0)
    policy = OfficialOpenPIDroidClient(transport, timeout_seconds=5.0, transport_is_thread_confined=True)
    observations: list[dict[str, object]] = []
    one_step: list[dict[str, object]] = []
    try:
        # No-control warm-up: the first compiled request must never be executed.
        warm_metric = reset(model, data, hand_id, target_id, TARGET_OFFSETS[0])
        renderer.update_scene(data, camera=free_camera(140.0, -25.0, 2.0))
        warm_exterior = renderer.render().copy()
        renderer.update_scene(data, camera=wrist_camera)
        warm_wrist = renderer.render().copy()
        warm_started = perf_counter()
        warm_response = policy.infer(DroidObservation(as_frame(warm_exterior), as_frame(warm_wrist), DroidRobotState(tuple(float(data.qpos[address]) for address in qpos_addresses), 0.5), "Warm up only; do not execute."))
        warmup = {"no_control": True, "client_rtt_ms": (perf_counter() - warm_started) * 1000, "response_horizon": warm_response.action_chunk.horizon}
        for target_index, offset in enumerate(TARGET_OFFSETS):
            split = "diagnostic" if target_index < DIAGNOSTIC_TARGET_COUNT else "held_out"
            for condition_index, condition in enumerate(VISUAL_CONDITIONS):
                metric = reset(model, data, hand_id, target_id, offset)
                initial_distance = metric.distance_meters(tuple(float(value) for value in data.xpos[hand_id]))
                oracle = oracle_joint_direction(model, data, hand_id, dof_addresses, metric.target_position)
                exterior_camera = free_camera(condition.exterior_azimuth, condition.exterior_elevation, condition.exterior_distance)
                renderer.update_scene(data, camera=exterior_camera)
                exterior = apply_visual_variant(renderer.render().copy(), condition, rng)
                renderer.update_scene(data, camera=wrist_camera)
                wrist = apply_visual_variant(renderer.render().copy(), condition, rng)
                if target_index == 0:
                    import imageio.v3 as iio
                    iio.imwrite(RESULT_ROOT / f"visual_{condition.name}.png", exterior)
                current = tuple(float(data.qpos[address]) for address in qpos_addresses)
                record: dict[str, object] = {"target_index": target_index, "split": split, "target_offset_m": offset, "visual_condition": condition.name, "initial_distance_m": initial_distance, "oracle_joint_direction": oracle}
                try:
                    started = perf_counter()
                    response = policy.infer(DroidObservation(as_frame(exterior), as_frame(wrist), DroidRobotState(current, 0.5), PROMPT))
                    raw_action = response.action_chunk.actions[0]
                    record.update({"client_rtt_ms": (perf_counter() - started) * 1000, "response_horizon": response.action_chunk.horizon, "raw_first_action": raw_action, "identity_oracle_cosine": cosine_alignment(raw_action[:7], oracle), "safe_hold": None})
                except Exception as error:
                    record.update({"safe_hold": f"{type(error).__name__}: {error}"})
                    observations.append(record)
                    continue
                observations.append(record)
                for interpretation in ACTION_INTERPRETATIONS:
                    metric = reset(model, data, hand_id, target_id, offset)
                    initial_distance = metric.distance_meters(tuple(float(value) for value in data.xpos[hand_id]))
                    clipped = execute_one_action(model, data, bridge, interpretation.apply(raw_action), qpos_addresses, arm_actuators, gripper_actuators)
                    final_distance = metric.distance_meters(tuple(float(value) for value in data.xpos[hand_id]))
                    one_step.append({"target_index": target_index, "split": split, "visual_condition": condition.name, "action_interpretation": interpretation.name, "initial_distance_m": initial_distance, "final_distance_m": final_distance, "progress_m": one_step_progress(initial_distance, final_distance), "bridge_clipped": clipped})
    finally:
        transport.close(force=True)
    groups: dict[str, dict[str, object]] = {}
    for split in ("diagnostic", "held_out"):
        for interpretation in ACTION_INTERPRETATIONS:
            rows = [row for row in one_step if row["split"] == split and row["action_interpretation"] == interpretation.name]
            groups[f"{split}/{interpretation.name}"] = {"n": len(rows), "mean_progress_m": mean(float(row["progress_m"]) for row in rows) if rows else None, "positive_progress_fraction": mean(float(row["progress_m"]) > 0.0 for row in rows) if rows else None, "clipped_fraction": mean(bool(row["bridge_clipped"]) for row in rows) if rows else None}
    successful_observations = [row for row in observations if row.get("safe_hold") is None]
    report = {"scope": "pre-registered one-step DROID-to-Panda embodiment mismatch diagnosis; no learned adapter, no action-map search, no task-success claim", "protocol": {"target_count": len(TARGET_OFFSETS), "diagnostic_target_count": DIAGNOSTIC_TARGET_COUNT, "held_out_target_count": len(TARGET_OFFSETS) - DIAGNOSTIC_TARGET_COUNT, "visual_conditions": [asdict(value) for value in VISUAL_CONDITIONS], "action_interpretations": [asdict(value) for value in ACTION_INTERPRETATIONS]}, "warmup": warmup, "policy_requests": len(observations), "safe_hold_requests": sum(row.get("safe_hold") is not None for row in observations), "mean_client_rtt_ms": mean(float(row["client_rtt_ms"]) for row in successful_observations) if successful_observations else None, "one_step_rows": len(one_step), "summary": groups, "observations": observations, "one_step": one_step}
    (RESULT_ROOT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("policy_requests", "safe_hold_requests", "mean_client_rtt_ms", "summary")}, indent=2))


if __name__ == "__main__":
    main()
