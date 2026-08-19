# Stage 20 - Pre-registered Panda Closed-loop Control Feasibility Ladder

## Question and boundary

This CPU/MuJoCo study tests whether the existing Panda action bridge, an
analytic DLS velocity reference, and a finite control horizon can complete a
geometrically reachable reach. It does **not** load or query pi05, train an
adapter, or evaluate cross-embodiment transfer. A feasible DLS control contract
would be necessary but insufficient evidence for a future VLA study; an
infeasible one would locate a limitation below the VLA layer.

## New independent split

All offsets are from the Panda hand at the `home` reset and use the existing
4-cm geometric success metric. None duplicates a Stage 17/18 target.

| Split | Target offsets (m) |
| --- | --- |
| Diagnostic | `(0.07,-0.04,0.01)`, `(0.09,-0.04,0.02)`, `(0.07,-0.06,0.03)`, `(0.10,-0.03,0.01)` |
| Final test | `(0.075,-0.045,0.025)`, `(0.095,-0.055,0.015)`, `(0.065,-0.065,0.02)`, `(0.105,-0.035,0.03)` |

## Frozen ladder

Every episode records the complete distance curve, final distance, success,
control steps, joint-limit/velocity bridge clips, and safety events. No policy
transport is present, so a safety event can only be an explicitly caught local
execution exception; no event is silently ignored.

1. **No-op:** physics steps with no newly issued arm command.
2. **Fixed raw-action bridge:** the existing `DroidLikePandaActionBridge` with
   fixed legal 8-D action `(0.20,-0.20,0.20,-0.20,0.20,-0.20,0.20,0.5)`.
   This is a deterministic bridge-path control, not a pi05 action or policy.
3. **Closed-loop DLS velocity teacher:** re-compute the damped least-squares
   joint velocity from current state each bridge cycle, then pass it through
   the same bridge. It is an analytic simulator oracle, not a learned policy,
   real controller, or VLA.
4. **Direct-position IK oracle:** Stage 14's independent DLS position solution
   sent to ordinary MuJoCo position actuators. It is a reachability reference,
   not an action-bridge or learned-policy result.

## Diagnostic-only control selection

The only selectable DLS conditions are declared before execution:

| Name | Bridge dt (s) | Episode steps |
| --- | ---: | ---: |
| `existing_40` | 1/15 | 40 |
| `existing_120` | 1/15 | 120 |
| `long_dt_120` | 0.20 | 120 |

Run all three only on the four diagnostic targets. Select the configuration
using this fixed lexicographic rule: all-target success first, then number of
successes, lower mean final distance, fewer steps, then smaller dt. The chosen
condition is frozen. Final-test targets are then run exactly once with no-op,
fixed raw-action bridge, the frozen DLS bridge, and direct-position IK.

## Decision rule

The control contract is feasible only if the frozen DLS bridge reaches all four
final-test targets at 4 cm with no safety events. Direct IK success alone shows
geometric solvability, not bridge feasibility. No-op/fixed-action failure and
DLS success would isolate the result to the analytic state-feedback control
contract; neither outcome supports a pi05 transfer claim.

Raw JSON and optional visual artifacts remain ignored/local or remote results;
public Git contains only code, protocol, and aggregate findings.

## Result (2026-08-19)

The CPU-only MuJoCo run completed with no policy server, pi05 request, adapter,
training, GPU allocation, safety event, or DLS bridge clip. The raw report is
retained at `/root/shared-nvme/openpi-robot-runtime/results/stage20_control_feasibility/report.json`.

| Diagnostic DLS condition | Successes | Mean final distance |
| --- | ---: | ---: |
| `existing_40` | 0 / 4 | 9.31 cm |
| `existing_120` | 0 / 4 | 13.03 cm |
| `long_dt_120` | 4 / 4 | 3.91 cm |

The diagnostic rule therefore froze `long_dt_120` for the one final-test run.

| Final-test arm | Successes | Mean final distance | Clips / safety events |
| --- | ---: | ---: | ---: |
| No-op | 0 / 4 | 10.30 cm | 0 / 0 |
| Fixed raw-action bridge | 0 / 4 | 86.77 cm | 328 / 0 |
| Closed-loop DLS velocity oracle | 3 / 4 | 4.12 cm | 0 / 0 |
| Direct-position IK oracle | 4 / 4 | 3.15 cm | 0 / 0 |

The DLS bridge reached three final targets in 7--8 steps at 3.87--3.94 cm, but
the fourth remained 4.75 cm after all 120 steps. Under the pre-registered
4/4 rule, this fixed DLS bridge/time contract is **not proven feasible**. The
direct-position result independently confirms geometric reachability only.
This blocks Stage 21 sequence-adapter training; it makes no pi05 transfer claim.
