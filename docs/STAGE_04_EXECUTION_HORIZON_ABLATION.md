# Stage 4 — Receding-Horizon Execution Window Ablation

Date: 2026-08-18
Scope: a short, reproducible software-only systems measurement using the
official local π0.5-DROID policy server.

## Question

With the same policy, prompt, static images, mock robot, and four total mock
execution steps, what changes when the runtime executes `k=1` versus `k=2`
actions from each action chunk before requesting a fresh chunk?

## Controls and boundary

- Model: verified official `pi05_droid` checkpoint on the remote RTX 4090.
- Transport: official `WebsocketClientPolicy` to `127.0.0.1:8000`.
- Inputs: two static zero-valued `224x224x3` RGB frames and one fixed prompt.
- Execution: `MockDroidRobot` only. No camera, simulator task, robot SDK, motor,
  or physical robot is involved.
- Total execution steps: four in both conditions.

This is a request-cadence/latency measurement, not a task-quality evaluation.

## Result

| Execution horizon k | Policy requests | Mean client RTT | Mean server inference | Mean policy inference |
| --- | ---: | ---: | ---: | ---: |
| 1 | 4 | 86.59 ms | 85.44 ms | 58.12 ms |
| 2 | 2 | 79.40 ms | 78.02 ms | 56.03 ms |

The `k=2` condition made half as many policy requests for the same number of
mock execution steps. It therefore reduces network/server request cadence, but
also leaves the runtime open-loop for one additional action. This experiment
does not establish which value is safer or produces better manipulation; that
requires a validated task environment and embodiment-specific safety review.

The full machine-readable artifact is retained remotely at
`/root/shared-nvme/openpi-robot-runtime/results/execution_horizon_ablation.json`.

## Integration finding: official client thread ownership

The official synchronous `WebsocketClientPolicy` creates its socket in its
constructor. Calling `infer` from a separate timeout-worker thread caused a
request to hang even while the server and official simple client were healthy.
The project adapter now supports `transport_is_thread_confined=True`, which
keeps that transport's send/receive pair on its owning thread.

This preserves protocol compatibility for the current controlled experiment,
but it is not a complete hard-deadline implementation: a production robot-side
deadline must use a cancellable transport or a dedicated process that owns the
connection, treats timeout as safe hold, and discards/reconnects after an
unconfirmed request.
