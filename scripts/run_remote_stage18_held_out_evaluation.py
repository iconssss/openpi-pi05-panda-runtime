"""Pre-registered held-out Stage 18 evaluation; never use its output for tuning.

Runs the Stage 17 held-out targets (8--11) and all six fixed visual conditions
for exactly 40 control steps per episode.  It reports every frozen adapter seed,
the raw identity bridge, and an analytic DLS reachability upper bound.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from math import ceil
from pathlib import Path
from statistics import mean
from time import perf_counter

import mujoco
import numpy as np
import torch

from openpi_robot_runtime.observation_builder import DroidObservation, DroidRobotState
from openpi_robot_runtime.official_openpi import OfficialOpenPIDroidClient
from openpi_robot_runtime.panda_bridge import DroidLikePandaActionBridge
from openpi_robot_runtime.remote_client import OpenPIWebsocketTransportFactory, ProcessOwnedTransport
from openpi_robot_runtime.stage18 import (
    STAGE17_HELD_OUT_TARGET_INDICES, STAGE18_EPISODE_STEPS, combine_residual_action, evaluation_variants,
)
from run_remote_pi05_panda_mismatch_diagnosis import (
    PROMPT, RESULT_ROOT as STAGE17_RESULT_ROOT, TARGET_OFFSETS, VISUAL_CONDITIONS,
    apply_visual_variant, as_frame, free_camera, handles, oracle_joint_direction, reset,
)


TASK_XML = Path("/root/shared-nvme/openpi-robot-runtime/assets/panda_menagerie/franka_emika_panda/project02_reach_task.xml")
RESULT_ROOT = Path("/root/shared-nvme/openpi-robot-runtime/results/stage18_held_out_evaluation")
TRAINING_ROOT = Path("/root/shared-nvme/openpi-robot-runtime/results/stage18_adapter_training")
SUCCESS_THRESHOLD_M = 0.04


class ResidualAdapter(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.net = torch.nn.Sequential(torch.nn.Linear(14, 64), torch.nn.ReLU(), torch.nn.Linear(64, 64), torch.nn.ReLU(), torch.nn.Linear(64, 7), torch.nn.Tanh())

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return self.net(value)


def p95(values: list[float]) -> float | None:
    return sorted(values)[min(len(values) - 1, ceil(0.95 * len(values)) - 1)] if values else None


def apply_command(model: mujoco.MjModel, data: mujoco.MjData, bridge: DroidLikePandaActionBridge, action: tuple[float, ...], qpos_addresses: tuple[int, ...], arm_actuators: tuple[int, ...], gripper_actuators: tuple[int, ...]) -> bool:
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


def load_adapters() -> dict[int, ResidualAdapter]:
    adapters: dict[int, ResidualAdapter] = {}
    for variant in evaluation_variants():
        if variant.adapter_seed is None:
            continue
        checkpoint = torch.load(TRAINING_ROOT / f"residual_adapter_seed_{variant.adapter_seed}.pt", map_location="cpu", weights_only=True)
        adapter = ResidualAdapter()
        adapter.load_state_dict(checkpoint["state_dict"])
        adapter.eval()
        adapters[variant.adapter_seed] = adapter
    return adapters


def run_episode(*, model: mujoco.MjModel, data: mujoco.MjData, renderer: mujoco.Renderer, wrist_camera: mujoco.MjvCamera, bridge: DroidLikePandaActionBridge, qpos_addresses: tuple[int, ...], dof_addresses: tuple[int, ...], arm_actuators: tuple[int, ...], gripper_actuators: tuple[int, ...], hand_id: int, target_id: int, target_index: int, condition_index: int, policy: OfficialOpenPIDroidClient | None, adapters: dict[int, ResidualAdapter]) -> list[dict[str, object]]:
    condition = VISUAL_CONDITIONS[condition_index]
    exterior_camera = free_camera(condition.exterior_azimuth, condition.exterior_elevation, condition.exterior_distance)
    episodes: list[dict[str, object]] = []
    for variant in evaluation_variants():
        metric = reset(model, data, hand_id, target_id, TARGET_OFFSETS[target_index])
        distances = [metric.distance_meters(tuple(float(value) for value in data.xpos[hand_id]))]
        rtts: list[float] = []
        clips = 0
        safe_hold: str | None = None
        for step in range(STAGE18_EPISODE_STEPS):
            current = tuple(float(data.qpos[address]) for address in qpos_addresses)
            if variant.kind == "dls_oracle":
                arm_action = oracle_joint_direction(model, data, hand_id, dof_addresses, metric.target_position)
                action = arm_action + (0.5,)
            else:
                renderer.update_scene(data, camera=exterior_camera)
                # Deterministic per state-independent episode/step noise; no result-driven variation.
                rng = np.random.default_rng(18_000_000 + target_index * 100_000 + condition_index * 1_000 + step)
                exterior = apply_visual_variant(renderer.render().copy(), condition, rng)
                renderer.update_scene(data, camera=wrist_camera)
                wrist = apply_visual_variant(renderer.render().copy(), condition, rng)
                try:
                    started = perf_counter()
                    response = policy.infer(DroidObservation(as_frame(exterior), as_frame(wrist), DroidRobotState(current, 0.5), PROMPT))
                    rtts.append((perf_counter() - started) * 1000)
                    raw_action = tuple(float(value) for value in response.action_chunk.actions[0])
                    if variant.adapter_seed is None:
                        action = raw_action
                    else:
                        feature = torch.tensor(current + raw_action[:7], dtype=torch.float32).unsqueeze(0)
                        with torch.inference_mode():
                            residual = tuple(float(value) for value in adapters[variant.adapter_seed](feature).squeeze(0))
                        action = combine_residual_action(raw_action, residual)
                except Exception as error:
                    safe_hold = f"{type(error).__name__}: {error}"
                    break
            clips += int(apply_command(model, data, bridge, action, qpos_addresses, arm_actuators, gripper_actuators))
            distances.append(metric.distance_meters(tuple(float(value) for value in data.xpos[hand_id])))
        final_distance = distances[-1]
        episodes.append({"variant": variant.name, "variant_kind": variant.kind, "adapter_seed": variant.adapter_seed, "target_index": target_index, "target_offset_m": TARGET_OFFSETS[target_index], "visual_condition": condition.name, "requested_steps": STAGE18_EPISODE_STEPS, "completed_steps": len(distances) - 1, "safe_hold": safe_hold, "safe_hold_count": int(safe_hold is not None), "bridge_clipped_steps": clips, "client_rtt_ms": rtts, "client_rtt_mean_ms": mean(rtts) if rtts else None, "client_rtt_p95_ms": p95(rtts), "distance_curve_m": distances, "initial_distance_m": distances[0], "final_distance_m": final_distance, "success_threshold_m": SUCCESS_THRESHOLD_M, "success": final_distance <= SUCCESS_THRESHOLD_M})
    return episodes


def main() -> None:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    model = mujoco.MjModel.from_xml_path(str(TASK_XML))
    data = mujoco.MjData(model)
    qpos_addresses, dof_addresses, arm_actuators, gripper_actuators, limits, hand_id, target_id = handles(model)
    bridge = DroidLikePandaActionBridge(limits)
    renderer = mujoco.Renderer(model, height=256, width=256)
    adapters = load_adapters()
    transport = ProcessOwnedTransport(OpenPIWebsocketTransportFactory("127.0.0.1", 8000), request_timeout_seconds=5.0, startup_timeout_seconds=10.0)
    policy = OfficialOpenPIDroidClient(transport, timeout_seconds=5.0, transport_is_thread_confined=True)
    episodes: list[dict[str, object]] = []
    try:
        wrist_camera = free_camera(30.0, -10.0, 0.65)
        for target_index in STAGE17_HELD_OUT_TARGET_INDICES:
            for condition_index in range(len(VISUAL_CONDITIONS)):
                episodes.extend(run_episode(model=model, data=data, renderer=renderer, wrist_camera=wrist_camera, bridge=bridge, qpos_addresses=qpos_addresses, dof_addresses=dof_addresses, arm_actuators=arm_actuators, gripper_actuators=gripper_actuators, hand_id=hand_id, target_id=target_id, target_index=target_index, condition_index=condition_index, policy=policy, adapters=adapters))
    finally:
        transport.close(force=True)
    summary: dict[str, dict[str, object]] = {}
    for variant in evaluation_variants():
        rows = [row for row in episodes if row["variant"] == variant.name]
        rtts = [value for row in rows for value in row["client_rtt_ms"]]
        summary[variant.name] = {"episodes": len(rows), "successes": sum(bool(row["success"]) for row in rows), "safe_holds": sum(int(row["safe_hold_count"]) for row in rows), "clipped_steps": sum(int(row["bridge_clipped_steps"]) for row in rows), "mean_final_distance_m": mean(float(row["final_distance_m"]) for row in rows) if rows else None, "mean_client_rtt_ms": mean(rtts) if rtts else None, "p95_client_rtt_ms": p95(rtts)}
    report = {"scope": "pre-registered held-out Stage 18 evaluation: frozen raw pi05 identity, every frozen residual-adapter seed, and analytic DLS reachability upper bound; held-out results must not tune, select, or retrain adapters", "experiment_boundary": {"stage17_held_out_target_indices": STAGE17_HELD_OUT_TARGET_INDICES, "visual_conditions": [asdict(value) for value in VISUAL_CONDITIONS], "steps_per_episode": STAGE18_EPISODE_STEPS, "success_threshold_m": SUCCESS_THRESHOLD_M, "policy_execution": "process-owned 5 s deadline; first action only; existing Panda safety bridge", "dls_oracle": "analytic reachability upper bound, not a learned policy", "stage17_reference": str(STAGE17_RESULT_ROOT / "report.json")}, "expected_episodes_per_variant": len(STAGE17_HELD_OUT_TARGET_INDICES) * len(VISUAL_CONDITIONS), "episodes": episodes, "summary": summary}
    (RESULT_ROOT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"expected_episodes_per_variant": report["expected_episodes_per_variant"], "summary": summary}, indent=2))


if __name__ == "__main__":
    main()
