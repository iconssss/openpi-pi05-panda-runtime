# Stage 18 - Frozen-Policy Safety-Bounded Panda Action Adapter

## Purpose

Stage 17 establishes that the raw pi05 DROID action has weak but non-random
one-step agreement with a Panda reach direction, while Stage 15 establishes
that this agreement is insufficient for a long-horizon reach. Stage 18 tests a
strictly narrower question: can a *frozen-policy*, bounded residual adapter
improve Panda simulator control without claiming that pi05 was fine-tuned or
that it natively controls Panda?

## Pre-registered split and data contract

- **Training and validation only:** randomized Panda states and targets sampled
  from the Stage 17 diagnostic target distribution. The random generator seed,
  accepted sample identifiers, and DLS reachability residual are saved.
- **Held-out evaluation only:** the four Stage 17 held-out target offsets and
  all six fixed visual conditions. They must not be used for early stopping,
  gain selection, or architecture changes.
- **Frozen policy input:** seven current Panda joint positions plus the first
  seven entries of the live pi05 action. The adapter receives no target
  coordinates, no simulator-only task metric, and no image pixels.
- **Label:** a bounded damped-least-squares Panda joint-velocity direction from
  the current state to the visible reach target. This is an analytic simulator
  expert, not a teleoperation dataset or a human demonstration.
- **Output:** an additive seven-dimensional residual. The combined action is
  clipped by the existing `DroidLikePandaActionBridge` and joint limits; the
  adapter cannot bypass transport deadlines, safe holds, or first-action-only
  execution.

## Baselines and outcome measures

1. Frozen raw pi05 identity bridge (Stage 15 / Stage 17 baseline).
2. DLS oracle (solvability upper bound; not a learned policy).
3. Frozen pi05 plus learned residual adapter.

The primary held-out measure is 40-step reach success at the existing 4 cm
threshold. Secondary measures are final distance, progress curve, safe holds,
joint-limit clipping, request latency, and generalization across the six visual
conditions. Results will report all seeds, not just the best seed.

## Resource and claim boundary

No OpenPI weights are updated. The pi05 server and the adapter training job run
sequentially because the server consumes about 20.9 GB of 24 GB VRAM. The
planned collection, training, and held-out evaluation budget is about 1--1.5
RTX 4090 hours (roughly RMB 2--3 at the stated rate), with data and results
stored under `/root/shared-nvme/openpi-robot-runtime/results/`.

## Held-out result (2026-08-19)

The evaluation was run once after training, with no held-out-driven tuning,
seed selection, or retraining. It used exactly Stage 17 held-out targets 8--11,
all six fixed visual conditions, and 40 first-action-only control steps per
episode: 24 episodes per arm. Raw JSON remains at
`/root/shared-nvme/openpi-robot-runtime/results/stage18_held_out_evaluation/report.json`.

| Arm | Successes | Safe holds | Mean final distance (m) | Mean / p95 pi05 RTT (ms) |
| --- | ---: | ---: | ---: | ---: |
| Raw pi05 identity | 0 / 24 | 0 | 0.17973 | 82.66 / 85.84 |
| Residual adapter seed 11 | 0 / 24 | 0 | 0.10350 | 82.39 / 85.47 |
| Residual adapter seed 22 | 0 / 24 | 0 | 0.10159 | 82.53 / 86.14 |
| Residual adapter seed 33 | 0 / 24 | 0 | 0.10519 | 82.34 / 85.34 |
| DLS oracle (analytic upper bound) | 0 / 24 | 0 | 0.10194 | n/a |

All 120 episodes completed all 40 steps, with zero bridge-clipped steps. The
common mean initial distance was 0.13601 m and success threshold was 0.04 m.
The three frozen adapters improve final distance versus raw identity, but none
establishes reach success; seed 22 is reported as one of all pre-registered
results, not selected as a winner. DLS is an analytic upper bound, not a
learned policy.
