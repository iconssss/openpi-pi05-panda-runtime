# Stage 14 - Controlled Panda reach task

## Task definition

A project-owned MuJoCo wrapper scene adds an independent static mocap target to
the immutable official Panda model. At reset, the target is placed at a fixed
`(+0.12, -0.08, +0.04)` m offset from the Panda hand position in the official
`home` keyframe. The target is not attached to the robot.

Success is an independently computed geometric condition:

```text
Euclidean distance(hand body origin, target) <= 0.04 m
```

The wrapper is project-owned; it does not edit any official Panda mesh or XML.
It is placed alongside the asset only because MuJoCo resolves the official
model's mesh directory relative to the top-level task XML.

## Baseline validation

| Baseline | Final hand-target distance | Success |
| --- | ---: | --- |
| 8-D zero DROID-like action | 19.33 cm | no |
| Deterministic bounded random (seed 7) | 21.09 cm | no |
| Damped least-squares IK oracle | 3.23 cm | yes |

The oracle has a 1.90 mm kinematic residual before controller execution. It is
an explicitly non-learned geometric solver used only to demonstrate that the
task and metric are solvable. It must never be reported as π0.5 performance.

No OpenPI server was started and no GPU was used in this stage.

Artifacts:

- `/root/shared-nvme/openpi-robot-runtime/results/panda_reach_baselines/report.json`
- `zero_droid_like_action.png`, `bounded_random_seed_7.png`, and
  `dls_ik_oracle.png` in the same result directory.

## Fair comparison rule for Stage 15

Any later bridge-path condition must use the identical target generation,
4-cm success threshold, reset keyframe, control-cycle budget, action bound,
and first-action-only execution convention. Its result remains a DROID-like
synthetic-observation interface measurement unless it is trained/evaluated with
appropriately matched Panda data and calibrated cameras.
