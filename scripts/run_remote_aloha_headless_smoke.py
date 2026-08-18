"""Validate Project 2's installed ALOHA MuJoCo environment in headless mode."""

from __future__ import annotations

import json
from pathlib import Path

import gymnasium as gym
import imageio.v3 as iio
import numpy as np

import gym_aloha  # Registers the environments.


def main() -> None:
    env = gym.make("gym_aloha/AlohaTransferCube-v0", render_mode="rgb_array")
    observation, info = env.reset(seed=7)
    action_spec = env.unwrapped._env.action_spec()
    qpos = env.unwrapped._env.physics.data.qpos.copy()
    first_frame = observation["top"]
    reward_trace: list[float] = []
    terminated = False
    for _ in range(5):
        observation, reward, terminated, truncated, info = env.step(
            np.zeros(env.action_space.shape, dtype=np.float32)
        )
        reward_trace.append(float(reward))
        if terminated or truncated:
            break
    root = Path("/root/shared-nvme/openpi-robot-runtime/results/aloha_headless_smoke")
    root.mkdir(parents=True, exist_ok=True)
    image_path = root / "transfer_cube_top_seed7.png"
    iio.imwrite(image_path, first_frame)
    report = {
        "scope": "headless simulator health check only; zero actions; no OpenPI action adapter or task-success claim",
        "environment": "gym_aloha/AlohaTransferCube-v0",
        "seed": 7,
        "observation_keys": sorted(observation.keys()),
        "top_image_shape": list(first_frame.shape),
        "top_image_dtype": str(first_frame.dtype),
        "action_shape": list(env.action_space.shape),
        "action_bounds": {"low": float(env.action_space.low.min()), "high": float(env.action_space.high.max())},
        "dm_control_action_spec": {
            "shape": list(action_spec.shape),
            "minimum": action_spec.minimum.tolist(),
            "maximum": action_spec.maximum.tolist(),
            "name": action_spec.name,
        },
        "physics_qpos_shape": list(qpos.shape),
        "physics_qpos_at_reset": qpos.tolist(),
        "zero_action_rewards": reward_trace,
        "terminated": terminated,
        "image_artifact": str(image_path),
    }
    (root / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    env.close()


if __name__ == "__main__":
    main()
