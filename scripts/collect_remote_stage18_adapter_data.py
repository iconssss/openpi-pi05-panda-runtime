"""Collect a frozen-pi05 / DLS-expert adapter dataset from diagnostic targets only."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter

import mujoco
import numpy as np

from openpi_robot_runtime.observation_builder import DroidObservation, DroidRobotState
from openpi_robot_runtime.official_openpi import OfficialOpenPIDroidClient
from openpi_robot_runtime.remote_client import OpenPIWebsocketTransportFactory, ProcessOwnedTransport
from run_remote_pi05_panda_mismatch_diagnosis import (
    DIAGNOSTIC_TARGET_COUNT,
    PROMPT,
    RESULT_ROOT as STAGE17_RESULT_ROOT,
    TARGET_OFFSETS,
    VISUAL_CONDITIONS,
    apply_visual_variant,
    as_frame,
    free_camera,
    handles,
    oracle_joint_direction,
    reset,
)


TASK_XML = Path("/root/shared-nvme/openpi-robot-runtime/assets/panda_menagerie/franka_emika_panda/project02_reach_task.xml")
RESULT_ROOT = Path("/root/shared-nvme/openpi-robot-runtime/results/stage18_adapter_data")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=128)
    parser.add_argument("--seed", type=int, default=20260819)
    args = parser.parse_args()
    if args.samples <= 0:
        raise ValueError("samples must be positive")
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    model, data = mujoco.MjModel.from_xml_path(str(TASK_XML)), None
    data = mujoco.MjData(model)
    qpos_addresses, dof_addresses, _, _, limits, hand_id, target_id = handles(model)
    renderer = mujoco.Renderer(model, height=256, width=256)
    wrist_camera = free_camera(30.0, -10.0, 0.65)
    rng = np.random.default_rng(args.seed)
    transport = ProcessOwnedTransport(OpenPIWebsocketTransportFactory("127.0.0.1", 8000), request_timeout_seconds=5.0, startup_timeout_seconds=10.0)
    policy = OfficialOpenPIDroidClient(transport, timeout_seconds=5.0, transport_is_thread_confined=True)
    rows: list[dict[str, object]] = []
    try:
        # Server must already have received an external no-control warm-up.
        for sample_index in range(args.samples):
            base_index = sample_index % DIAGNOSTIC_TARGET_COUNT
            base_offset = np.asarray(TARGET_OFFSETS[base_index])
            offset = tuple(float(value) for value in base_offset + rng.uniform(-0.008, 0.008, size=3))
            metric = reset(model, data, hand_id, target_id, offset)
            for address, (lower, upper) in zip(qpos_addresses, limits, strict=True):
                data.qpos[address] = np.clip(data.qpos[address] + rng.uniform(-0.12, 0.12), lower, upper)
            mujoco.mj_forward(model, data)
            condition = VISUAL_CONDITIONS[sample_index % len(VISUAL_CONDITIONS)]
            exterior_camera = free_camera(condition.exterior_azimuth, condition.exterior_elevation, condition.exterior_distance)
            renderer.update_scene(data, camera=exterior_camera)
            exterior = apply_visual_variant(renderer.render().copy(), condition, rng)
            renderer.update_scene(data, camera=wrist_camera)
            wrist = apply_visual_variant(renderer.render().copy(), condition, rng)
            current = tuple(float(data.qpos[address]) for address in qpos_addresses)
            oracle = oracle_joint_direction(model, data, hand_id, dof_addresses, metric.target_position)
            started = perf_counter()
            try:
                response = policy.infer(DroidObservation(as_frame(exterior), as_frame(wrist), DroidRobotState(current, 0.5), PROMPT))
                rows.append({"sample_index": sample_index, "base_diagnostic_target_index": base_index, "target_offset_m": offset, "visual_condition": condition.name, "joint_position": current, "raw_pi05_arm_action": response.action_chunk.actions[0][:7], "dls_oracle_velocity": oracle, "client_rtt_ms": (perf_counter() - started) * 1000, "safe_hold": None})
            except Exception as error:
                rows.append({"sample_index": sample_index, "base_diagnostic_target_index": base_index, "target_offset_m": offset, "visual_condition": condition.name, "joint_position": current, "safe_hold": f"{type(error).__name__}: {error}"})
    finally:
        transport.close(force=True)
    report = {"scope": "frozen pi05 diagnostic-distribution collection for Stage 18 residual-adapter training; no held-out target is sampled", "requested_samples": args.samples, "completed_samples": sum(row["safe_hold"] is None for row in rows), "safe_holds": sum(row["safe_hold"] is not None for row in rows), "seed": args.seed, "stage17_report_reference": str(STAGE17_RESULT_ROOT / "report.json"), "rows": rows}
    (RESULT_ROOT / f"pilot_{args.samples}_seed_{args.seed}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("requested_samples", "completed_samples", "safe_holds", "seed")}, indent=2))


if __name__ == "__main__":
    main()
