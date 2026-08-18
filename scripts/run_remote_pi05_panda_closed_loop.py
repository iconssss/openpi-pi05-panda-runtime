"""Five re-observation π0.5/Panda interface cycles with first-action execution.

This is an observability and deadline experiment, not a manipulation benchmark:
the Panda views are synthetic free-camera proxies and there is no task object or
success predicate.
"""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter

import imageio.v3 as iio
import mujoco
import numpy as np

from openpi_robot_runtime.observation_builder import DroidObservation, DroidRobotState, RGBFrame
from openpi_robot_runtime.official_openpi import OfficialOpenPIDroidClient
from openpi_robot_runtime.panda_bridge import DroidLikePandaActionBridge
from openpi_robot_runtime.remote_client import OpenPIWebsocketTransportFactory, ProcessOwnedTransport


ASSET_ROOT = Path("/root/shared-nvme/openpi-robot-runtime/assets/panda_menagerie/franka_emika_panda")
RESULT_ROOT = Path("/root/shared-nvme/openpi-robot-runtime/results/pi05_panda_closed_loop")
PROMPT = "Move the Panda end effector safely in simulation."
REPLAN_COUNT = 5


def frame(image: np.ndarray) -> RGBFrame:
    rows = np.linspace(0, image.shape[0] - 1, 224).astype(np.intp)
    columns = np.linspace(0, image.shape[1] - 1, 224).astype(np.intp)
    return RGBFrame(224, 224, image[rows][:, columns, :3].astype(np.uint8, copy=False).tobytes())


def camera(azimuth: float, elevation: float, distance: float) -> mujoco.MjvCamera:
    value = mujoco.MjvCamera()
    value.type = mujoco.mjtCamera.mjCAMERA_FREE
    value.azimuth, value.elevation, value.distance = azimuth, elevation, distance
    value.lookat[:] = (0.0, 0.0, 0.45)
    return value


def handles(model: mujoco.MjModel) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...], tuple[tuple[float, float], ...]]:
    ids = tuple(mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, f"joint{i}") for i in range(1, 8))
    if any(identifier < 0 for identifier in ids):
        raise RuntimeError("Expected Panda joint1..joint7 are unavailable.")
    qpos = tuple(int(model.jnt_qposadr[identifier]) for identifier in ids)
    transmission_ids = tuple(int(model.actuator_trnid[index, 0]) for index in range(model.nu))
    arm = tuple(transmission_ids.index(identifier) for identifier in ids)
    gripper = tuple(index for index in range(model.nu) if index not in arm)
    if not gripper:
        raise RuntimeError("Panda gripper actuator was not resolved.")
    return qpos, arm, gripper, tuple(tuple(float(v) for v in model.jnt_range[i]) for i in ids)


def main() -> None:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    model = mujoco.MjModel.from_xml_path(str(ASSET_ROOT / "scene.xml"))
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    qpos_addresses, arm_actuators, gripper_actuators, limits = handles(model)
    bridge = DroidLikePandaActionBridge(limits)
    physics_steps = max(1, round(bridge.control_dt_seconds / model.opt.timestep))
    renderer = mujoco.Renderer(model, height=256, width=256)
    exterior_camera = camera(140, -25, 2.0)
    wrist_camera = camera(30, -10, 0.65)
    transport = ProcessOwnedTransport(
        OpenPIWebsocketTransportFactory("127.0.0.1", 8000),
        request_timeout_seconds=5.0,
        startup_timeout_seconds=10.0,
    )
    policy = OfficialOpenPIDroidClient(transport, timeout_seconds=5.0, transport_is_thread_confined=True)
    trace: list[dict[str, object]] = []
    safe_hold: str | None = None
    try:
        for step in range(REPLAN_COUNT):
            current = tuple(float(data.qpos[address]) for address in qpos_addresses)
            renderer.update_scene(data, camera=exterior_camera)
            exterior = renderer.render().copy()
            renderer.update_scene(data, camera=wrist_camera)
            wrist = renderer.render().copy()
            if step == 0:
                iio.imwrite(RESULT_ROOT / "exterior_step0.png", exterior)
                iio.imwrite(RESULT_ROOT / "wrist_step0.png", wrist)
            observation = DroidObservation(frame(exterior), frame(wrist), DroidRobotState(current, 0.5), PROMPT)
            started = perf_counter()
            response = policy.infer(observation)
            wall_ms = (perf_counter() - started) * 1000
            action = response.action_chunk.actions[0]
            command = bridge.to_position_command(current_joint_positions=current, droid_like_action=action)
            for actuator, target in zip(arm_actuators, command.joint_position_targets, strict=True):
                data.ctrl[actuator] = target
            for actuator in gripper_actuators:
                low, high = (float(value) for value in model.actuator_ctrlrange[actuator])
                data.ctrl[actuator] = low + command.gripper_normalized * (high - low)
            for _ in range(physics_steps):
                mujoco.mj_step(model, data)
            trace.append(
                {
                    "step": step,
                    "client_round_trip_ms": wall_ms,
                    "server_infer_ms": response.server_infer_ms,
                    "policy_infer_ms": response.policy_infer_ms,
                    "first_action": action,
                    "bridge_clipped": command.clipped,
                    "joint_before": current,
                    "joint_after": tuple(float(data.qpos[address]) for address in qpos_addresses),
                }
            )
    except Exception as error:
        safe_hold = f"{type(error).__name__}: {error}"
    finally:
        transport.close(force=True)
    report = {
        "scope": "five-replan Panda interface stress test; synthetic cameras; no task or transfer-performance claim",
        "requested_replans": REPLAN_COUNT,
        "completed_replans": len(trace),
        "physics_steps_per_first_action": physics_steps,
        "safe_hold": safe_hold,
        "clipped_replans": sum(bool(item["bridge_clipped"]) for item in trace),
        "trace": trace,
    }
    (RESULT_ROOT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
