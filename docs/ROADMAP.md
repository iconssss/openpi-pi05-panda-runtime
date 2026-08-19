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
4. **Stage 16 - interview package (complete).** Architecture diagram,
   failure-mode table, experiment summary, cost/resource notes, and an honest
   limitations/real-robot readiness checklist are recorded.
5. **Stage 17 - embodiment-mismatch diagnosis (complete).** A pre-registered
   12-target / 6-visual-condition / 3-action-interpretation one-step study
   completed 72 live requests with zero safe holds. Identity is directionally
   preferable to the two diagnostic alternatives, but its millimetre-scale
   progress is insufficient for a transfer claim.
6. **Stage 18 - frozen-policy action-adapter study (complete).** A
   diagnostic-target-only DLS-labelled dataset trained three frozen bounded
   residual adapters. Held-out evaluation used exactly Stage 17 targets 8--11
   and six fixed visual conditions (24 episodes / arm, 40 steps / episode).
   All 120 episodes completed with zero safe holds; raw pi05 identity and all
   adapters were 0/24 successes at 4 cm. Adapters reduced mean final distance
   from 0.17973 m (raw) to 0.10350 / 0.10159 / 0.10519 m (seeds 11/22/33), but
   do not support a Panda task-success or native-transfer claim. The analytic
   DLS reference was also 0/24 at this 40-step horizon and is not learned.
7. **Stage 19 - multi-step failure attribution and robustness analysis
   (complete).** Read-only analysis of every Stage 18 held-out trajectory
   identifies raw late-horizon divergence (+24.21 mm over the final ten steps)
   and adapter/DLS late-horizon regression (+2.62 to +7.10 mm), with zero
   safe holds and bridge clips. It intentionally does not claim residual,
   joint-limit, or state-distribution causality because those per-step signals
   were not logged. Any Stage 20 training proposal requires a new pre-registered
   training distribution and independent test set.
8. **Stage 20 - control feasibility ladder (complete).** New diagnostic/final
   target splits isolated CPU-only Panda control from pi05. Diagnostic selection
   froze a 0.20-s, 120-step DLS bridge (4/4 diagnostic), but it reached only
   3/4 final targets; direct-position IK reached 4/4. Thus the fixed bridge/time
   contract is not proven feasible, so Stage 21 sequence-adapter training is
   blocked. This is not a pi05 transfer result.
9. **Stage 20B - low-level control-contract replication (complete).** A new
   split and diagnostic-only condition selection froze the Stage 20 reference
   DLS contract. It achieved 4/4 new final targets with zero clips/safety
   events (3.87 cm mean); direct IK also achieved 4/4. This unlocks a future,
   separately pre-registered Stage 21 study, but proves only analytic Panda
   simulator control feasibility and nothing about pi05 transfer.
10. **Stage 21A - frozen Cartesian intent probe (complete, negative).** On a
    target-level held-out split, state+real pi05 MLP MSE (0.01369) did not beat
    state-only (0.01133), and did not pass its shuffled-control gate. No target
    ID proxy was found, but direction labels are concentrated (constant cosine
    0.848), so high cosine is not transfer evidence. Stage 21B is blocked.
11. **Stage 22 - counterfactual intent benchmark (pre-registered, CPU gate
    passed).** Exact same-state ±X/±Y/±Z task pairs have balanced directions,
    zero constant-direction cosine, and 1/6 state-only condition chance. No
    pi05 collection is authorized by this record alone; any such collection
    requires a separate approval after reviewing this benchmark.

## GPU policy

The 4090 is used for loaded π0.5 inference experiments only. Each future run
must begin with a no-control warm-up, retain a process-owned deadline and safe
hold, write results to `/root/shared-nvme/openpi-robot-runtime/results`, and
SIGTERM-stop the server after collection. Model loading uses about 20.9 GB of
the 24 GB GPU; concurrent GPU workloads are not supported.
