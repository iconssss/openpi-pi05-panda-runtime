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
