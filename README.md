# OpenPI π0.5 Remote Inference & Robot Action Adapter

An interview-oriented VLA systems project. It demonstrates a safe ownership
boundary around a remotely hosted OpenPI π0.5 policy:

```text
robot-side observation
  -> typed DROID request
  -> official OpenPI WebSocket client / policy server
  -> action chunk (H x 8)
  -> embodiment adapter
  -> safety filter
  -> execution of only the first k actions
  -> re-observation and replanning
```

The policy server never directly controls an actuator. This repository owns
request validation, deadlines, action adaptation, safety filtering, execution
cadence, and metrics.

## Verified status — 2026-08-18

- A dedicated remote OpenPI environment was created at
  `/root/shared-nvme/conda-envs/openpi-runtime`; CUDA was verified on an RTX
  4090 without modifying Project 1.
- The official `pi05_droid` checkpoint was fully verified: all 20 official GCS
  objects match their paths and exact byte sizes (12,429,488,598 bytes).
- The official `scripts/serve_policy.py` server restored the checkpoint,
  passed `/healthz`, and completed the official DROID simple-client smoke test.
- `OfficialOpenPIDroidClient` serializes the project's typed DROID observation
  using the official WebSocket client and validates a finite `(H, 8)` response.
- A real-server closed-loop software smoke test completed two independent
  replans. Each action chunk was passed through the local adapter and safety
  layer, then executed only by `MockDroidRobot` using static zero test images.
  This is not a physical-robot deployment or task-success evaluation.
- A controlled `k=1` versus `k=2` execution-window measurement is recorded:
  four versus two policy requests for four fixed mock steps, respectively.
  It measures request cadence and latency only; it does not claim task quality.
- A 60-request GPU-backed latency profile measured 78.54 ms mean / 81.49 ms p95
  client round trip on one local WebSocket connection; see Stage 5 for scope.
- The runtime now ends in a traceable safe hold when policy/action processing
  fails; one real-response-plus-controlled-fault test verified no extra mock
  command is issued after the fault.
- A process-owned transport now terminates an unconfirmed WebSocket request and
  requires a fresh connection before recovery; this path is validated live.
- A live `pi05_droid` request using synthetic Panda free-camera proxies returned
  an H=15 action chunk; only its first action was bridge-limited and executed in
  MuJoCo. The cold request required a 33.20 s no-control warm-up, while the warm
  guarded request completed in 211.33 ms. This validates the software boundary,
  not Panda transfer or task success.
- A warm five-cycle Panda re-observation loop completed all 5 replans under a
  process-owned 5 s deadline. Cycles 1--4 averaged about 81.10 ms client RTT;
  every command was still bridge-limited. This is a control-path measurement,
  not a manipulation evaluation.
- A 200-request, five-condition synthetic-observation Panda stress experiment
  completed with no safe holds. Mean/p95 client RTT were 82.61/88.15 ms. It is
  evidence for the bounded system path under valid synthetic inputs only.
- Stage 13 consolidates cold-start, warm-path, safety, and stress metrics into
  a lightweight local SVG/JSON/Markdown analysis bundle for interview use.
- Stage 14 defines a Panda geometric reach task with an independent 4-cm metric;
  zero/random controls fail while a non-learned IK oracle validates solvability.
- Stage 15 runs π0.5 on five IK-reachable Panda targets (200 requests): the
  system path is stable but reaches 0/5 successes, an explicit negative result
  that prevents an unsupported transfer claim.
- Stage 17 turns that negative result into a pre-registered embodiment-mismatch
  diagnosis: 72/72 live requests completed with no safe holds. The identity
  action interpretation had positive one-step geometric progress on 2/3 of
  diagnostic cases and 5/8 of held-out cases, but only at millimetre scale;
  this does not contradict the Stage 15 0/5 long-horizon result.
- Stage 18 evaluates three frozen diagnostic-target-trained bounded residual
  adapters only on the Stage 17 held-out four targets and six fixed visual
  conditions. All 120 forty-step episodes completed without safe holds, but
  raw identity and every adapter remained 0/24 successes at the 4-cm threshold.
  Adapters reduced mean final distance from 0.17973 m (raw) to
  0.10350/0.10159/0.10519 m (seeds 11/22/33); this is not a Panda skill or
  native-transfer claim, and no seed was selected from held-out results.
- Stage 19 is a no-GPU, read-only analysis of every Stage 18 trajectory. It
  finds late-horizon distance regression after initial adapter/DLS progress,
  with zero safe holds and bridge clips. The logged data cannot separately
  identify residual-vector error, joint-limit proximity, or state-distribution
  shift; those are Stage 20 hypotheses, not conclusions.
- Stage 20 separates the controller contract from VLA transfer using a new
  target split and CPU-only MuJoCo ladder. Direct-position IK succeeds 4/4,
  while the diagnostic-selected closed-loop DLS bridge reaches only 3/4 final
  targets; the fixed bridge/time contract is not yet proven feasible,
  independently of pi05.
- Stage 20B repairs and independently replicates the low-level analytic control
  contract on a new split: a diagnostic-frozen DLS velocity bridge reaches 4/4
  final targets at 3.87 cm mean, alongside direct-position IK at 4/4. This is
  low-level simulator feasibility only, not π0.5, adapter, or real-robot skill.
- Stage 16 packages the architecture, evidence table, interview narrative and
  strict presentation boundaries for this project portfolio entry.
- Headless MuJoCo/EGL and ALOHA smoke testing now pass. ALOHA is deliberately
  rejected as a direct π0.5-DROID target because its dual-arm action and camera
  contract is incompatible.
- The official MuJoCo Menagerie Panda 7-DoF asset is complete at
  `/root/shared-nvme/openpi-robot-runtime/assets/panda_menagerie`: 80/80 files
  and 36,560,926 bytes were verified against the immutable official commit
  `da76818e269b82289eba39808e2fb91d679d6994`. Panda bridge validation is the
  next simulator stage; this is not yet a policy-performance result.

The remote policy server is currently stopped after verification, so the GPU is
free. Checkpoints, logs, and result artifacts remain on the remote shared disk.

## Local verification

Run on Windows PowerShell; this package intentionally has no OpenPI/GPU runtime
dependency on the local machine:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

## Important boundaries

- The current DROID contract is seven joint-velocity values plus one gripper
  position. It is not a universal robot-action API.
- `prediction horizon H` belongs to the model; `execution horizon k` belongs to
  this runtime. The runtime executes only the first `k` actions before it
  observes and requests a fresh chunk.
- A real embodiment requires a separately reviewed robot SDK adapter, calibrated
  camera preprocessing, coordinate/unit checks, hardware limits, and safety
  approval. None are claimed here.

## Records

- [Project memory and decisions](PROJECT_MEMORY.md)
- [Stage 0: official source research](docs/STAGE_00_RESEARCH.md)
- [Stage 1: mock runtime](docs/STAGE_01_MOCK_RUNTIME.md)
- [Stage 2: environment and storage](docs/STAGE_02_ENVIRONMENT.md)
- [Stage 3: checkpoint and official policy server](docs/STAGE_03_CHECKPOINT_AND_SERVER.md)
- [Stage 4: execution-horizon ablation](docs/STAGE_04_EXECUTION_HORIZON_ABLATION.md)
- [Stage 5: latency profile](docs/STAGE_05_LATENCY_PROFILE.md)
- [Stage 6: fail-safe fault injection](docs/STAGE_06_FAIL_SAFE_FAULT_INJECTION.md)
- [Stage 7: process-owned deadline transport](docs/STAGE_07_PROCESS_OWNED_DEADLINE_TRANSPORT.md)
- [Stage 8: simulator readiness](docs/STAGE_08_SIMULATION_READINESS.md)
- [Stage 9: Panda DROID-like bridge smoke](docs/STAGE_09_PANDA_BRIDGE.md)
- [Stage 10: live pi05 Panda interface smoke](docs/STAGE_10_LIVE_PI05_PANDA_SMOKE.md)
- [Stage 11: warm Panda re-observation loop](docs/STAGE_11_PANDA_CLOSED_LOOP.md)
- [Stage 12: 200-request Panda stress experiment](docs/STAGE_12_PANDA_STRESS.md)
- [Stage 13: latency and safety analysis](docs/STAGE_13_ANALYSIS.md)
- [Stage 14: controlled Panda reach task](docs/STAGE_14_PANDA_REACH_TASK.md)
- [Stage 15: live π0.5 Panda reach suite](docs/STAGE_15_REACH_SUITE.md)
- [Stage 16: interview package](docs/STAGE_16_INTERVIEW_PACKAGE.md)
- [Stage 17: embodiment-mismatch diagnosis](docs/STAGE_17_EMBODIMENT_MISMATCH.md)
- [Stage 18: frozen-policy action-adapter study](docs/STAGE_18_FROZEN_POLICY_ACTION_ADAPTER.md)
- [Stage 19: multi-step failure analysis](docs/STAGE_19_MULTISTEP_FAILURE_ANALYSIS.md)
- [Stage 20: control feasibility ladder](docs/STAGE_20_CONTROL_FEASIBILITY.md)
- [Stage 20B: control-contract replication](docs/STAGE_20B_CONTROL_CONTRACT_REPLICATION.md)
- [Results at a glance](docs/RESULTS_AT_A_GLANCE.md)
- [Forward plan](docs/ROADMAP.md)
