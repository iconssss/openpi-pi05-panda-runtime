# Stage 20B - Pre-registered Low-level Control-contract Repair and Replication

## Research question and scope

Can a bounded, interpretable DLS velocity-control contract reach a new Panda
final-test split at 4 cm without pi05, adapters, training, or GPU inference?
This is CPU-only MuJoCo. DLS and direct IK are analytic simulator oracles, not
learned policies, real-robot controllers, or VLA results. A positive result
would establish only this low-level Panda control contract.

## Independent targets and reachability record

Offsets are relative to the Panda hand at `home`; each episode logs an
independently recomputed direct-IK residual before execution. These targets do
not duplicate Stage 17/18 held-out or Stage 20 final targets.

| Split | Offsets (m) |
| --- | --- |
| Development/diagnostic | `(0.06,-0.03,0.01)`, `(0.08,-0.05,0.02)`, `(0.09,-0.03,0.015)`, `(0.07,-0.06,0.02)` |
| Final test | `(0.065,-0.035,0.015)`, `(0.085,-0.045,0.020)`, `(0.075,-0.055,0.010)`, `(0.095,-0.040,0.020)` |

There is no stochastic target sampling; the recorded seed is `20260819` as an
explicit reproducibility identifier, not a source of target selection.

## Diagnostic-only DLS conditions

The teacher is `Jᵀ(JJᵀ + λ²I)⁻¹ error`, then a linear slowdown of
`min(1, ||error|| / slowdown_radius)` before passing the seven velocity values
through the existing Panda bridge. `max_joint_velocity` is the bridge's explicit
velocity limit. The 4-cm threshold is unchanged.

| Name | Damping λ | Max velocity | dt (s) | Steps | Slowdown radius (m) |
| --- | ---: | ---: | ---: | ---: | ---: |
| `stage20_reference` | 0.010 | 1.00 | 0.20 | 120 | none |
| `damped_slow_200` | 0.032 | 0.50 | 0.10 | 200 | 0.08 |
| `low_speed_long_240` | 0.010 | 0.35 | 0.10 | 240 | 0.08 |
| `medium_slow_180` | 0.022 | 0.50 | 0.15 | 180 | 0.06 |

All four run only on development targets. Select one frozen condition by:
highest success count; then lowest mean final distance; then fewest bridge
clips; then declaration order. No final-test row is visible to this selection.

## One-shot final-test ladder

After selection, run the new final targets exactly once with no-op, the Stage
20 fixed raw-action bridge, the frozen DLS velocity contract, and direct-
position IK. Record full distance curves, success, final distance, actual
control steps, bridge clips, explicit safety events, and IK residual.

The DLS contract succeeds only at 4/4 final success with no safety event.
Anything else blocks sequence-adapter training. Raw JSON stays ignored or under
remote results; Git contains only sources, protocol, and aggregates.

## Result (2026-08-19)

The CPU-only run made no pi05 request, did not start a server, and used no GPU,
adapter, or training. The raw report remains at
`/root/shared-nvme/openpi-robot-runtime/results/stage20b_control_contract/report.json`.

| Development condition | Successes | Mean final distance | Clips |
| --- | ---: | ---: | ---: |
| `stage20_reference` | 4 / 4 | 3.82 cm | 0 |
| `damped_slow_200` | 0 / 4 | 8.80 cm | 0 |
| `low_speed_long_240` | 0 / 4 | 8.79 cm | 0 |
| `medium_slow_180` | 0 / 4 | 5.93 cm | 0 |

The pre-registered rule uniquely froze `stage20_reference`: damping 0.010,
max velocity 1.00, dt 0.20 s, 120 steps, no slowdown. The maximum development
direct-IK residual was 1.02 mm.

| Final-test arm | Successes | Mean final distance | Clips / safety events |
| --- | ---: | ---: | ---: |
| No-op | 0 / 4 | 9.30 cm | 0 / 0 |
| Stage 20 fixed raw-action bridge | 0 / 4 | 86.04 cm | 328 / 0 |
| Frozen closed-loop DLS velocity contract | 4 / 4 | 3.87 cm | 0 / 0 |
| Direct-position IK oracle | 4 / 4 | 3.17 cm | 0 / 0 |

The four final DLS episodes completed in 5/7/6/8 steps at 3.74/3.95/3.85/3.95
cm, with IK residuals 0.246/0.047/0.394/0.495 mm. The 4/4 feasibility criterion
is therefore met on this independent final split.

This permits, but does not itself perform or validate, a separately
pre-registered Stage 21 sequence-aware adapter study. It proves only that this
specific low-level analytic Panda control contract is feasible in simulation;
it does not establish pi05 transfer, adapter success, real-robot control,
calibration, sim-to-real transfer, or safety certification.
