# Stage 19 - Pre-registered Multi-step Failure Attribution and Robustness Analysis

## Question

Stage 18 reduced held-out mean final distance while every arm remained below the
4-cm success criterion. Stage 19 is a **read-only secondary analysis** of the
already completed Stage 18 report. It asks which failure patterns are supported
by the logged trajectories, and which causal explanations remain unidentifiable.

## Frozen input and exclusions

- Input is only `/root/shared-nvme/openpi-robot-runtime/results/stage18_held_out_evaluation/report.json`.
- The analysis includes all five pre-registered arms, all 24 episodes per arm,
  the four Stage 17 held-out targets, six fixed visual conditions, and all 40
  recorded steps. No rows, seeds, conditions, or targets may be removed.
- It starts no policy server, makes no policy request, changes no bridge limit,
  and trains no model. It therefore has no GPU cost and cannot influence any
  Stage 18 result.

## Measures

For each arm, target, and visual condition, report episode count, success/safe
hold/clip counts, initial/final distance, net distance change, minimum observed
distance, mean distance curve, and the last-ten-step distance change. A compact
SVG reports the five mean curves on the common 40-step horizon.

The analysis compares each frozen adapter and DLS against raw identity only as
a descriptive difference in final distance. It does not choose a seed. DLS is
always labelled an analytic control/reachability reference, never a learned
policy.

## Attribution rules and limits

1. **Visual and target robustness:** compare the complete grouped distributions;
   their ranges identify where final outcomes vary, but do not establish a
   causal visual-perception mechanism.
2. **Multi-step accumulation:** use full curves and late-horizon change to
   distinguish initial progress from drift/stall. This is descriptive, not a
   controller stability proof.
3. **Control horizon/reference:** DLS at the same bridge and 40-step horizon
   provides an upper-bound reference for this fixed experiment. Its failure to
   cross 4 cm cannot be attributed to learning or model inference.
4. **Not identifiable:** Stage 18 did not log per-step Panda joint state,
   raw-versus-adapter residual vectors, or an unclipped target command. Thus it
   cannot separately estimate action-residual error, joint-limit proximity, or
   state-distribution shift. Zero bridge clips only rules out observed bridge
   clipping as the direct explanation. These signals require a newly
   pre-registered Stage 20 data contract and an independent test set.

## Decision boundary

Stage 19 can recommend a future hypothesis, but may not alter an adapter,
select seed 22 (or any seed), or claim a successful controller. A future Stage
20 proposal must pre-register a new training distribution and independent test
split before collecting data or training a model.

## Result (2026-08-19)

The analyzer consumed the full 120-episode report once. It generated ignored
local artifacts under `artifacts/stage19/`; the authoritative input remains the
remote Stage 18 JSON. No server was started and no GPU work occurred.

| Arm | Net mean distance change | Mean minimum distance | Last 10-step change | Interpretation |
| --- | ---: | ---: | ---: | --- |
| Raw identity | +43.71 mm | 132.65 mm | +24.21 mm | Early minimum is near reset distance, followed by sustained divergence. |
| Adapter seed 11 | -32.52 mm | 94.66 mm | +5.91 mm | Substantial initial progress, then late regression. |
| Adapter seed 22 | -34.42 mm | 95.69 mm | +2.62 mm | Same pattern; listed, not selected. |
| Adapter seed 33 | -30.82 mm | 96.28 mm | +5.68 mm | Same pattern; listed, not selected. |
| DLS reference | -34.07 mm | 92.39 mm | +7.10 mm | Fixed-horizon analytic reference also stalls/regresses. |

Adapter final-distance reductions versus raw were 76.23 mm (seed 11), 78.14 mm
(seed 22), and 74.54 mm (seed 33); DLS was 77.79 mm lower than raw. This does
not change the shared 0/24 success result. Across visual conditions, the raw
mean final distance ranged 0.17171--0.18466 m; adapter target-wise ranges were
larger than their visual ranges, but the small fixed grid cannot establish a
causal perceptual or geometric source.

The strongest supported failure statement is therefore: the frozen residual
mapping improves distance over raw identity but does not sustain convergence at
the existing bridge/time horizon, and observed transport failure or bridge
clipping did not cause the misses. It is not valid to attribute the remaining
error to a particular adapter residual, joint limit, or train/test state shift
from this log alone.
