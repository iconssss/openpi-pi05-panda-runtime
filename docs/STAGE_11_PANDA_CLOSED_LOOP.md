# Stage 11 - Warm Panda re-observation closed loop

Date: 2026-08-18

## Experiment

After the no-control π0.5 warm-up described in Stage 10, the runtime performed
five consecutive simulation cycles. Each cycle rendered fresh synthetic exterior
and wrist proxy views from the current Panda state, made a process-owned
WebSocket policy request with a 5 s deadline, selected only action row zero,
applied the explicit Panda bridge, and advanced 33 MuJoCo steps (approximately
one 1/15 s bridge interval).

## Result

All 5/5 requested replans completed with no safe hold. Every replan triggered
at least one bridge clamp because the initial/default Panda pose conflicts with
one or more XML joint bounds; the clamp is expected evidence that limits are
being enforced, not a policy-quality metric.

| Cycle | Client RTT (ms) | Server inference (ms) | Policy inference (ms) |
| --- | ---: | ---: | ---: |
| 0 | 188.82 | 93.08 | 58.57 |
| 1 | 81.71 | 79.67 | 57.59 |
| 2 | 79.43 | 78.07 | 55.56 |
| 3 | 81.25 | 79.71 | 55.80 |
| 4 | 82.00 | 80.43 | 55.81 |

The first warm-phase request remains slower; cycles 1--4 averaged about
81.10 ms client RTT. This must not be compared to a real robot control rate
without adding sensor acquisition, controller, and robot-SDK timing.

## Boundary

There is no task object, reward, calibrated camera, or Panda demonstration data
in this experiment. The changing joint state and newly rendered images prove
the re-observation/replan plumbing, not that π0.5 understands the Panda scene
or can manipulate successfully.

Artifact: `/root/shared-nvme/openpi-robot-runtime/results/pi05_panda_closed_loop/report.json`.
The policy server was SIGTERM-stopped after the run; the 4090 returned to 1 MiB
allocated.
