# Project 2 forward plan

## Completed evidence

Stages 0--12 establish: isolated remote OpenPI runtime; verified official
checkpoint; live WebSocket inference; deadline-safe reconnect behavior;
MuJoCo/EGL validation; verified official Panda asset; explicit 8-D action
bridge; live one-step and re-observation loops; and a 200-request stress run.

## Next work, in order

1. **Stage 13 - analysis artifact (complete).** Local JSON/Markdown/SVG bundle
   consolidates the cold-start, warm-path and safe-hold evidence.
2. **Stage 14 - controlled task environment (complete).** A geometric Panda
   reach task now has fixed reset logic, a 4-cm independent metric, failed zero/
   random baselines, and a successful non-learned IK solvability oracle.
3. **Stage 15 - task-level bridge evaluation (complete).** Five IK-reachable
   targets / 200 policy requests completed with zero safety failures but 0/5
   task successes. The negative result correctly distinguishes reliable
   infrastructure from unsupported cross-embodiment skill claims.
4. **Stage 16 - interview package.** Produce architecture diagram, failure-mode
   table, experiment summary, cost/resource notes, and an honest limitations/
   real-robot readiness checklist.

## GPU policy

The 4090 is used for loaded π0.5 inference experiments only. Each future run
must begin with a no-control warm-up, retain a process-owned deadline and safe
hold, write results to `/root/shared-nvme/openpi-robot-runtime/results`, and
SIGTERM-stop the server after collection. Model loading uses about 20.9 GB of
the 24 GB GPU; concurrent GPU workloads are not supported.
