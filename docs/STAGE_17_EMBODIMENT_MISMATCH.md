# Stage 17 - Pre-registered DROID-to-Panda Embodiment-Mismatch Diagnosis

## Question

The Stage 15 0/5 result can arise from visual geometry, observation convention,
joint/action semantics, or their interaction.  This stage measures those
mismatches before any learned adapter is trained.  It does not search for a
successful mapping and does not claim Panda task success.

## Fixed protocol

- 12 deterministic target offsets from the Panda `home` reset.  Targets 0--7
  are marked **diagnostic**; targets 8--11 are **held out**.  A future adapter
  may be designed from diagnostic data only and must report held-out results.
- Six visual conditions: canonical free camera; two azimuth shifts; elevation
  shift; brightness reduction; and deterministic RGB noise.  The second
  synthetic wrist camera remains fixed.
- Each target/visual pair creates exactly one live pi05 DROID request after a
  no-control warm-up: 72 policy requests total.
- The first returned action is evaluated from an identical reset under three
  predeclared action interpretations: identity, global arm sign negation, and
  identity at quarter gain.  These are diagnostic probes, not candidates to be
  selected as a deployed controller.
- Primary measures: process-owned request safe holds, warm RTT, action cosine
  against a damped-least-squares Panda direction oracle, and one-step reduction
  in independently measured hand-to-target distance.  Positive one-step
  progress is favorable; it is not reach-task success.

## Controls against overclaiming

No joint permutation, per-joint sign search, camera selection, target selection,
or gain selection is optimized on this report.  All simulator resets, safety
limits, first-action execution, and the 5-second process-owned deadline retain
the Stage 15 configuration.  Any learned Stage 18 adapter must freeze this
held-out split before training.

## Resource budget

The loaded official policy occupies about 20.9 GB of the 24 GB RTX 4090.  This
experiment uses no new package, model, dataset, or persistent cache and writes
only a small JSON report plus six PNG diagnostics to the project's remote
`results/` directory.  It is expected to take several minutes including policy
load and warm-up, rather than consuming GPU hours by artificial repetition.

## Result (2026-08-18)

The protocol completed exactly 72/72 live pi05 requests after a separate
no-control warm-up. There were zero process-deadline safe holds; mean client
round-trip time was 83.41 ms. The identity action vector had mean cosine 0.271
against the local DLS joint-space direction oracle, with a positive cosine in
83.3% of requests. This measures local action-direction agreement only.

| Split | Fixed interpretation | Cases | Mean one-step progress | Positive-progress fraction |
| --- | --- | ---: | ---: | ---: |
| Diagnostic | identity | 48 | +0.107 mm | 66.7% |
| Diagnostic | global arm negation | 48 | -0.512 mm | 14.6% |
| Diagnostic | identity, quarter gain | 48 | -0.119 mm | 43.8% |
| Held out | identity | 24 | +0.231 mm | 62.5% |
| Held out | global arm negation | 24 | -0.704 mm | 8.3% |
| Held out | identity, quarter gain | 24 | -0.113 mm | 25.0% |

The held-out identity outcome is directionally consistent with diagnostic data,
so the raw DROID action convention is a better local probe than global sign
reversal. However, the improvement is only one-step and millimetre-scale;
Stage 15 remains the task-level result: zero of five long-horizon reaches.
This report therefore motivates a bounded learned action adapter, not a claim
of zero-shot DROID-to-Panda transfer.

Remote artifact:
`/root/shared-nvme/openpi-robot-runtime/results/pi05_panda_mismatch_diagnosis/report.json`.
The policy server was SIGTERM-stopped after collection and the 4090 returned to
0% utilization / 1 MiB allocation.
