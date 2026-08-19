# Project 3 Plan — Visual Diffusion Policy for Held-out ManiSkill Manipulation

## Unique recommendation

Build **“Visual Diffusion Policy for Held-out ManiSkill Pick-and-Place
Generalization.”** Use one ManiSkill 3 tabletop manipulation task with RGB-D
camera observations plus robot proprioception, generate bounded expert
demonstrations in simulation, train a conditional diffusion action-chunk policy
on one RTX 4090, and report closed-loop success on held-out object poses and
visual domain shifts.

This is the best complement to Project 2: it supplies the missing positive
learned-policy capability without disguising a target-specific fine-tune as
zero-shot transfer. It also differs from a likely ACT-focused Project 1 by
making diffusion action generation, visual generalization, and held-out
closed-loop evaluation central.

## Why this direction over alternatives

| Direction | Algorithm / VLA relevance | Credible positive result | Single-4090 fit | Cost / risk | Decision |
| --- | --- | --- | --- | --- | --- |
| Diffusion Policy in ManiSkill | High / Medium | High with scripted experts and narrow task | High | Moderate, controllable | **Choose** |
| ACT in ManiSkill / RoboSuite | High / Medium | High | High | Lower novelty if Project 1 already covers ACT | Baseline only if needed |
| LIBERO imitation benchmark | High / High | Medium | Medium | Heavier data/preprocessing and long debugging risk | Defer |
| OpenPI target-domain fine-tuning | High / High | Medium | Low–Medium | Large checkpoint/data/schema risk; Project 2 stop boundary | Do not use |
| Vision IL generalization benchmark without diffusion | Medium / Medium | Medium | High | Useful component, weaker policy-training story | Fold into evaluation |
| ROS2 / simulator-control project | Robotics systems High / VLA Low | Medium | High | Does not fill learned-policy gap | Future systems project |

## Research question

Can a visual diffusion action-chunk policy trained on bounded ManiSkill expert
demonstrations retain high closed-loop pick-and-place success on **unseen object
poses and visual perturbations**, and which observation/action-history choices
matter most?

## Task, data, and environment

- **Environment:** ManiSkill 3, one officially supported single-arm tabletop
  pick-and-place task (exact task/version/asset commit frozen in Stage 0).
- **Training distribution:** scripted/trajectory-planner expert demonstrations
  over object pose ranges and a fixed visual set; save deterministic episode
  IDs, seeds, camera setup, actions, and normalization statistics.
- **Final test:** untouched pose seeds plus visual variants (lighting, texture,
  distractor-free background changes) that remain task-equivalent. No final
  episode informs model choice.
- **Claim boundary:** simulator-only imitation learning and simulation
  generalization; no real-robot or sim-to-real claim.

## Baselines and model

1. No-op / random action sanity controls.
2. Behavioral-cloning MLP from proprioception only.
3. Visual behavioral-cloning deterministic action-chunk baseline.
4. **Primary:** RGB-D + proprioception conditional diffusion policy producing a
   normalized 8–16 step continuous action chunk, receding-horizon execution.

Keep the vision encoder compact (frozen small CNN or lightweight trainable CNN,
chosen before data collection); use a U-Net/temporal diffusion action head.
Normalize observations/actions with training split statistics only. Train at
least three seeds; do not select a seed on final test.

## Closed-loop evaluation and ablations

Primary metric is episode success rate with exact environment success signal.
Also report final object-to-goal distance, collision/termination rate, action
smoothness, inference latency, and 95% binomial confidence intervals.

Pre-register ablations: (a) visual+proprioception versus proprioception-only,
(b) diffusion versus deterministic BC, and (c) action horizon 8 versus 16.
Choose a single configuration on validation only; evaluate the final test once.

## Success standard

The project succeeds only if the diagnostic-selected diffusion configuration:

- reaches at least **80% final-test success** across at least 50 unseen-pose
  episodes and all three training seeds have mean success at least 75%; and
- beats visual deterministic BC by at least 15 percentage points on the same
  final test, with no increase in catastrophic collision/termination rate.

Anything lower is reported as an honest trained-policy result, not rounded into
success. A failed gate ends the task iteration and triggers analysis rather than
unbounded hyperparameter search.

## Resource envelope

Estimate **12–20 GPU hours** on one 24-GB RTX 4090: 1–2 h environment/data
generation checks, 6–12 h training across three seeds and selected ablation,
and 2–4 h evaluation/reproducibility. Expected storage is **20–60 GB** for
compressed demonstrations, checkpoints, and videos; set a 70-GB cap and keep
all large artifacts off C: and out of Git. Validate exact feasibility before
download because this is a new project and must use isolated paths/environment.

## Six-stage roadmap

1. **Stage 0 — scope lock:** choose task/version, success metric, hardware and
   storage plan; pre-register train/validation/final pose and visual splits.
2. **Stage 1 — environment + expert:** CPU/GPU-free smoke, scripted expert
   validation, dataset schema, normalization and data-integrity audits.
3. **Stage 2 — baselines:** no-op/random/proprio BC and visual BC with fixed
   validation selection rules.
4. **Stage 3 — diffusion training:** three seeds under a declared budget;
   checkpoint and metric retention policy.
5. **Stage 4 — one-shot held-out evaluation:** closed-loop success, robustness,
   latency, failure cases, confidence intervals and videos.
6. **Stage 5 — portfolio package:** reproducibility guide, evidence table,
   ablation figure, costs, interview story, and explicit simulator boundary.
