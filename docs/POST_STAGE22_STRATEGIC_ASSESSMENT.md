# Post-Stage-22 Strategic Route Assessment

## Decision context

The frozen DROID-action route has now been tested at the appropriate levels:
remote deployment and safety boundaries; zero-shot Panda reach; one-step
diagnosis; frozen residual adaptation; full-trajectory analysis; independent
low-level DLS-contract feasibility; target-level incremental-information
probing; and a balanced, exact-same-state counterfactual benchmark. Stage 20B
removes the low-level Panda velocity contract as the principal remaining
explanation. Stage 22 then finds no held-out incremental Cartesian intent in
the final DROID action versus either state-only or shuffled controls.

This is a sufficient negative-evidence chain to **close frozen DROID
robot-facing action transfer as the primary Project 2 research line**. It is
not evidence that the π0.5/VLM backbone has no task semantics, nor evidence
about real robots or sim-to-real transfer.

## What the completed portfolio can honestly claim

The project is credibly a **Safe VLA cross-embodiment deployment and failure
attribution study**. It demonstrates the official checkpoint/server boundary,
typed observations, process-owned deadline/reconnect, safe hold, action-chunk
ownership, explicit DROID-to-Panda constraints, MuJoCo task evaluation, and a
sequence of independent negative-result controls.

It cannot claim Panda skill, real-robot control, calibrated perception,
sim-to-real transfer, safety certification, zero-shot embodiment transfer, or
that a residual adapter solved the task. Its strongest interview differentiator
is not a cherry-picked success: it isolates transport, geometry, low-level
control, state shortcuts, direction imbalance, and shuffled-feature controls
before closing an unsupported hypothesis. The principal weakness is the lack
of a learned positive manipulation result. A successful result is not required
for a credible systems/research portfolio, provided the README is reorganized
around evidence and limits and the accompanying architecture, benchmark,
latency, and failure-analysis visuals are completed.

## Route comparison

Scores are relative to the current Project 2 state: High is favorable, while
cost, complexity, time risk, and overlap use Low as favorable.

| Dimension | A: close line | B: upstream latent probe | C: target fine-tune | D: freeze + Project 3 |
| --- | --- | --- | --- | --- |
| Research value | High | High | Medium | High |
| Robotics-role relevance | High | High | High | High |
| VLA-role relevance | Medium | High | High | High |
| Resume expressiveness | High | High | Medium | High |
| Interview depth | High | High | Medium | High |
| Credible positive-result chance | n/a | Medium | Medium | High |
| Negative-result value | High | High | Medium | Low |
| GPU cost | Low | Medium | High | Medium |
| Storage cost | Low | Low | High | Medium |
| Engineering complexity | Low | Medium | High | High |
| Time risk | Low | Medium | High | Medium |
| Overlap with existing work | Low | Medium | High | Low |
| Incremental learning | Medium | High | Medium | High |
| Transfer to future robot work | High | High | Medium | High |

### A — formally close after Stage 22

This is already scientifically defensible and should happen regardless of the
next choice: no more post-hoc action adapters. A focused packaging pass
(README evidence architecture, system diagram, benchmark graphic, result table,
interview Q&A, short safe-runtime demo/GIF and latency visual) has high
portfolio ROI with negligible GPU risk. A alone leaves the upstream semantic
question unresolved, which is the one remaining narrow ambiguity worth testing.

### B — Stage 23 upstream representation feasibility

This directly separates “task semantics absent” from “task semantics entangled
by the DROID action decoder,” while reusing the already validated Stage 22
counterfactual split and controls. The installed official source shows that
`Pi0.embed_prefix` produces image/language tokens and that action sampling
computes action-expert `suffix_out` before `action_out_proj`; the public
`sample_actions` currently returns only actions. Thus a small, checkpoint-
preserving instrumentation patch is required, but no model parameter changes
are needed. This is the highest-information remaining experiment.

### C — target-embodiment-specific fine-tuning

The official source contains a `pi05_droid_finetune` configuration and
`scripts/train.py`; its declared default is 20,000 steps with batch size 32.
It therefore establishes that an official-style route exists, but not that it
is a cheap, reliable 24-GB-single-4090 experiment. Panda data would require a
new observation/action schema, training-only normalization statistics, a
separate train/validation/final split, and checkpoints on shared storage.
MuJoCo DLS/IK trajectories could support **target-embodiment adaptation in
simulation only**. Without real Panda demonstrations, it cannot support real
robot generalization. It also risks looking like “fine-tune until success” and
is not recommended before resolving whether the frozen upstream representation
contains useful task-conditioned information.

### D — freeze Project 2 and start Project 3

Project 3 would have greater marginal value after one bounded Stage 23 answer
or immediately if its opportunity cost is urgent. It should target an explicit
positive task outcome (e.g., imitation/diffusion-policy training and evaluation
in ManiSkill, RoboSuite, or LIBERO) with a new dataset/evaluation story, rather
than continuing unbounded adaptation here.

## Recommendation: B once, then A/D

Run only the pre-registered Stage 23 representation probe. If its held-out gate
fails, freeze all π0.5-to-Panda adaptation work, perform Route A portfolio
packaging, and begin Route D. If it passes, report the limited representation
finding and still require a separately justified decision before any Panda
fine-tuning; it does not unlock an adapter by itself.

**Stop rule:** if Stage 23 does not exceed both final-action and shuffled-latent
controls on the locked Stage 22 held-out groups, stop all π0.5→Panda adaptation
experiments. Do not redesign the feature, recollect the same test set, or try a
new adapter. Freeze Project 2 after packaging and redirect effort to Project 3.

**GPU ceiling:** at most **2 additional RTX 4090 GPU-hours** for the entire
remaining Project 2 research path: an instrumentation smoke plus one frozen
Stage 23 extraction. No fine-tuning is authorized within this ceiling. A server
load/warm-up, extraction, and immediate SIGTERM are mandatory; stop sooner if
the pilot shows missing/degenerate latent output. Storage is capped at 2 GB of
new remote Stage 23 artifacts by pooling/casting features, with raw images not
persisted.
