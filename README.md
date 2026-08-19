# Safe VLA Cross-Embodiment Deployment and Failure Attribution

An interview-oriented embodied-AI systems study of a deliberately difficult
question: can a frozen **OpenPI π0.5 DROID** policy be deployed through a safe,
explicit action bridge to a Panda MuJoCo reach task?

**Bottom line:** the remote inference and safety runtime work reliably, but
frozen DROID robot-facing actions did not demonstrate transferable Panda reach
skill. The project is intentionally frozen after pre-registered negative
evidence and a failed instrumentation-validity gate—not extended until a
positive result appears.

![Project 2 evidence chain](docs/PROJECT2_EVIDENCE_CHAIN.svg)

## What I built

```text
Panda observation
  -> typed DROID observation
  -> official OpenPI WebSocket policy server
  -> H x 8 DROID action chunk
  -> explicit DROID-to-Panda bridge
  -> limits / safe hold / first-k execution
  -> MuJoCo re-observation and replanning
```

The robot-side runtime owns schema validation, a process-owned 5-second
deadline, reconnect after an unconfirmed request, action limits, safe hold,
execution-window ownership, and metrics. The policy server never directly owns
an actuator.

## The evidence in two minutes

| Question | Strongest evidence | Result |
| --- | --- | --- |
| Does the remote policy path work safely? | Official checkpoint/server, bounded transport, 200-request stress run | Yes: valid protocol path; 0 safe holds in stress. |
| Does frozen DROID action transfer solve Panda reach? | Five reachable targets / 200 requests | No: 0/5 successes. |
| Is this only a weak action-map issue? | Stage 17 one-step test; Stage 18 frozen residual adapters | Weak millimetre signal and lower distance, but every held-out adapter episode remains 0/24 success. |
| Is Panda's low-level controller the bottleneck? | Independent Stage 20B DLS velocity contract | No: analytic DLS reaches 4/4 independent final targets. |
| Does final π0.5 action add task intent beyond state? | Target-level probe and exact-same-state six-direction counterfactuals | No locked held-out incremental-information gate passes. |
| Can an upstream latent rescue that conclusion? | Stage 23 action-equivalence preflight | Not answered: instrumentation changed the action feature above tolerance; full extraction was stopped. |

The complete synthesis is in [Final Project Summary](docs/FINAL_PROJECT_SUMMARY.md).

## What this proves—and what it does not

**Supported**

- An official π0.5 DROID checkpoint can be hosted remotely behind a typed,
  deadline-bounded, safe action-runtime boundary.
- Explicit cross-embodiment action constraints and independent simulator
  controls make failure attribution more credible than an end-to-end demo.
- For this Panda MuJoCo setup, the frozen final DROID action did not provide
  sufficient held-out, task-conditioned Cartesian information beyond controls.

**Not supported**

- Real robot control, calibrated camera performance, safety certification,
  sim-to-real transfer, zero-shot Panda skill, or a successful learned Panda
  policy.
- A claim that π0.5 lacks semantics upstream: Stage 23 is an instrumentation
  validity failure, not a representation negative result.

## Final status

Project 2 is frozen for experimentation. No further π0.5→Panda adapter, latent
instrumentation, LoRA, fine-tuning, recurrent policy, or benchmark redesign is
authorized. The next work is portfolio packaging and a separate Project 3 that
trains and evaluates a learned manipulation policy with a positive held-out
success criterion.

## Reading order

1. [Final Project Summary](docs/FINAL_PROJECT_SUMMARY.md)
2. [Core results](docs/RESULTS_AT_A_GLANCE.md)
3. [Interview guide](docs/INTERVIEW_GUIDE.md)
4. [Stage 18 adapter study](docs/STAGE_18_FROZEN_POLICY_ACTION_ADAPTER.md)
5. [Stage 20B controller feasibility](docs/STAGE_20B_CONTROL_CONTRACT_REPLICATION.md)
6. [Stage 22 counterfactual benchmark](docs/STAGE_22_COUNTERFACTUAL_INTENT_BENCHMARK.md)
7. [Stage 23 preflight stop](docs/STAGE_23_UPSTREAM_REPRESENTATION_PROBE.md)
8. [Project 3 plan](docs/PROJECT_3_PLAN.md)

## Local verification

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

Raw checkpoints, images, datasets, logs, and remote connection information are
intentionally excluded from GitHub.
