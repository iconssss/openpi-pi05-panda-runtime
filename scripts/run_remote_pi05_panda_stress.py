"""Longer bounded π0.5/Panda interface stress experiment.

The camera variants are deliberately synthetic.  This benchmark measures
transport, deadline, and action-bridge behavior under valid input variation;
it is not a manipulation-robustness or cross-embodiment-transfer claim.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from math import ceil, sqrt
from pathlib import Path
from statistics import mean
from time import perf_counter

import mujoco
import numpy as np

from openpi_robot_runtime.observation_builder import DroidObservation, DroidRobotState, RGBFrame
from openpi_robot_runtime.official_openpi import OfficialOpenPIDroidClient
from openpi_robot_runtime.panda_bridge import DroidLikePandaActionBridge
from openpi_robot_runtime.remote_client import OpenPIWebsocketTransportFactory, ProcessOwnedTransport


ASSET_ROOT = Path("/root/shared-nvme/openpi-robot-runtime/assets/panda_menagerie/franka_emika_panda")
RESULT_ROOT = Path("/root/shared-nvme/openpi-robot-runtime/results/pi05_panda_stress")
PROMPT = "Move the Panda end effector safely in simulation."
REPLANS_PER_CONDITION = 40


@dataclass(frozen=True)
class Condition:
    name: str
    exterior_azimuth_delta: float = 0.0
    brightness_gain: float = 1.0
    noise_stddev: float = 0.0


CONDITIONS = (
    Condition("nominal"),
    Condition("exterior_azimuth_plus_15", exterior_azimuth_delta=15.0),
    Condition("exterior_azimuth_minus_15", exterior_azimuth_delta=-15.0),
    Condition("dark_gain_0_55", brightness_gain=0.55),
    Condition("rgb_noise_stddev_18", noise_stddev=18.0),
)


def as_frame(image: np.ndarray) -> RGBFrame:
    rows = np.linspace(0, image.shape[0] - 1, 224).astype(np.intp)
    columns = np.linspace(0, image.shape[1] - 1, 224).astype(np.intp)
    return RGBFrame(224, 224, image[rows][:, columns, :3].astype(np.uint8, copy=False).tobytes())


def synthetic_variant(image: np.ndarray, condition: Condition, rng: np.random.Generator) -> np.ndarray:
    value = image.astype(np.float32) * condition.brightness_gain
    if condition.noise_stddev:
        value += rng.normal(0.0, condition.noise_stddev, size=value.shape)
    return np.clip(value, 0, 255).astype(np.uint8)


def free_camera(azimuth: float, elevation: float, distance: float) -> mujoco.MjvCamera:
    value = mujoco.MjvCamera()
    value.type = mujoco.mjtCamera.mjCAMERA_FREE
    value.azimuth, value.elevation, value.distance = azimuth, elevation, distance
    value.lookat[:] = (0.0, 0.0, 0.45)
    return value


def panda_handles(model: mujoco.MjModel) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...], tuple[tuple[float, float], ...]]:
    joint_ids = tuple(mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, f"joint{i}") for i in range(1, 8))
    if any(identifier < 0 for identifier in joint_ids):
        raise RuntimeError("Expected Panda joint1..joint7 are unavailable.")
    qpos_addresses = tuple(int(model.jnt_qposadr[identifier]) for identifier in joint_ids)
    transmission_ids = tuple(int(model.actuator_trnid[index, 0]) for index in range(model.nu))
    arm_actuators = tuple(transmission_ids.index(identifier) for identifier in joint_ids)
    gripper_actuators = tuple(index for index in range(model.nu) if index not in arm_actuators)
    if not gripper_actuators:
        raise RuntimeError("Panda gripper actuator was not resolved.")
    limits = tuple(tuple(float(value) for value in model.jnt_range[identifier]) for identifier in joint_ids)
    return qpos_addresses, arm_actuators, gripper_actuators, limits


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, ceil(fraction * len(ordered)) - 1)]


def main() -> None:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    model = mujoco.MjModel.from_xml_path(str(ASSET_ROOT / "scene.xml"))
    data = mujoco.MjData(model)
    qpos_addresses, arm_actuators, gripper_actuators, limits = panda_handles(model)
    bridge = DroidLikePandaActionBridge(limits)
    physics_steps = max(1, round(bridge.control_dt_seconds / model.opt.timestep))
    midpoint = tuple((lower + upper) / 2.0 for lower, upper in limits)
    renderer = mujoco.Renderer(model, height=256, width=256)
    wrist_camera = free_camera(30, -10, 0.65)
    transport = ProcessOwnedTransport(
        OpenPIWebsocketTransportFactory("127.0.0.1", 8000),
        request_timeout_seconds=5.0,
        startup_timeout_seconds=10.0,
    )
    policy = OfficialOpenPIDroidClient(transport, timeout_seconds=5.0, transport_is_thread_confined=True)
    condition_reports: list[dict[str, object]] = []
    all_rtts: list[float] = []
    all_server_ms: list[float] = []
    all_policy_ms: list[float] = []
    total_clipped = 0
    total_completed = 0
    try:
        for condition_index, condition in enumerate(CONDITIONS):
            mujoco.mj_resetData(model, data)
            for address, value in zip(qpos_addresses, midpoint, strict=True):
                data.qpos[address] = value
            mujoco.mj_forward(model, data)
            rng = np.random.default_rng(20260818 + condition_index)
            exterior_camera = free_camera(140 + condition.exterior_azimuth_delta, -25, 2.0)
            trace: list[dict[str, object]] = []
            safe_hold: str | None = None
            for step in range(REPLANS_PER_CONDITION):
                current = tuple(float(data.qpos[address]) for address in qpos_addresses)
                renderer.update_scene(data, camera=exterior_camera)
                exterior = synthetic_variant(renderer.render().copy(), condition, rng)
                renderer.update_scene(data, camera=wrist_camera)
                wrist = synthetic_variant(renderer.render().copy(), condition, rng)
                observation = DroidObservation(as_frame(exterior), as_frame(wrist), DroidRobotState(current, 0.5), PROMPT)
                try:
                    started = perf_counter()
                    response = policy.infer(observation)
                    client_ms = (perf_counter() - started) * 1000
                    action = response.action_chunk.actions[0]
                    command = bridge.to_position_command(current_joint_positions=current, droid_like_action=action)
                    for actuator, target in zip(arm_actuators, command.joint_position_targets, strict=True):
                        data.ctrl[actuator] = target
                    for actuator in gripper_actuators:
                        lower, upper = (float(value) for value in model.actuator_ctrlrange[actuator])
                        data.ctrl[actuator] = lower + command.gripper_normalized * (upper - lower)
                    for _ in range(physics_steps):
                        mujoco.mj_step(model, data)
                    trace.append(
                        {
                            "step": step,
                            "client_round_trip_ms": client_ms,
                            "server_infer_ms": response.server_infer_ms,
                            "policy_infer_ms": response.policy_infer_ms,
                            "bridge_clipped": command.clipped,
                            "first_action_l2": sqrt(sum(value * value for value in action)),
                        }
                    )
                    all_rtts.append(client_ms)
                    if response.server_infer_ms is not None:
                        all_server_ms.append(response.server_infer_ms)
                    if response.policy_infer_ms is not None:
                        all_policy_ms.append(response.policy_infer_ms)
                    total_completed += 1
                    total_clipped += int(command.clipped)
                except Exception as error:
                    safe_hold = f"{type(error).__name__}: {error}"
                    break
            condition_reports.append(
                {
                    "condition": condition.name,
                    "requested_replans": REPLANS_PER_CONDITION,
                    "completed_replans": len(trace),
                    "safe_hold": safe_hold,
                    "clipped_replans": sum(bool(item["bridge_clipped"]) for item in trace),
                    "client_rtt_mean_ms": mean([float(item["client_round_trip_ms"]) for item in trace]) if trace else None,
                    "client_rtt_p95_ms": percentile([float(item["client_round_trip_ms"]) for item in trace], 0.95),
                    "trace": trace,
                }
            )
    finally:
        transport.close(force=True)
    report = {
        "scope": "200-request synthetic Panda interface stress test; no task, reward, calibration, transfer, or hardware-performance claim",
        "conditions": condition_reports,
        "requested_total_replans": len(CONDITIONS) * REPLANS_PER_CONDITION,
        "completed_total_replans": total_completed,
        "safe_hold_conditions": sum(condition["safe_hold"] is not None for condition in condition_reports),
        "clipped_replans": total_clipped,
        "physics_steps_per_first_action": physics_steps,
        "aggregate": {
            "client_rtt_mean_ms": mean(all_rtts) if all_rtts else None,
            "client_rtt_p95_ms": percentile(all_rtts, 0.95),
            "server_infer_mean_ms": mean(all_server_ms) if all_server_ms else None,
            "policy_infer_mean_ms": mean(all_policy_ms) if all_policy_ms else None,
        },
    }
    (RESULT_ROOT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
