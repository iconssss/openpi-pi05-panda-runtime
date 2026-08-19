# Stage 21A - Pre-registered Frozen pi05 Cartesian Intent Probe

## Question and hypothesis

Does frozen pi05-DROID action output add measurable Cartesian motion-intent
information beyond current Panda proprioception? This is a representation probe,
not a closed-loop success optimization or sequence-adapter study.

The primary hypothesis is deliberately falsifiable: on unseen target IDs,
`state + real pi05` must beat both `state only` and `state + shuffled pi05`.
Otherwise frozen pi05 provides no measurable incremental Cartesian intent under
this setup.

## Controlled dataset

Stage 18 rows do not contain a complete action chunk, Cartesian label, or a
target-level train/validation/final split, so a new collection is required.
Frozen pi05 is queried using the established process-owned 5-s deadline and
Stage 20B Panda contract. No pi05 weight, backbone, or adapter is trained.

There are 24 deterministic target offsets, each with 60 randomized Panda joint
states (1,440 requested samples). Target IDs define the split: IDs 0--15 train
(960), 16--19 validation (240), 20--23 final held-out test (240). A deterministic
RNG seed `20260821` drives joint perturbations and the six fixed Stage 17 visual
conditions cycle by sample index. The target split never changes after this
document is published.

Raw rows retain target/hand pose, target ID, visual condition, sample ID, state,
action chunk, and request/safety metadata only under remote results. None is
committed to GitHub.

## Label, inputs, and leakage boundary

The primary label is Cartesian translation direction:

```text
y = (p_target - p_hand) / max(||p_target - p_hand||, 1e-9)
```

`p_target` and `p_hand` are used only offline to create the label and grouped
analysis. Probe inputs are limited to:

- Panda proprioception: current seven joint positions and gripper scalar;
- frozen pi05 first action (8-D); and, where declared, the fixed 8-D mean over
  the returned action chunk.

The action feature is the fixed 16-D concatenation `[first_action, chunk_mean]`.
The target Cartesian position/pose, Cartesian error, DLS command/output, IK
solution, target ID, future state/action, success label, and any target-derived
field are forbidden inputs. Dataset audit must reject rows missing a finite
action chunk or violating these dimensions.

## Models and controls

For each model class, fit B0 state-only, B1 pi05-only, B2 state+real-pi05, and
B3 state+shuffled-pi05. B3 permutes training action features only, with shuffle
seeds 101/202/303; validation and final inputs remain real features. No B3
shuffle crosses target splits.

- Linear ridge probe (fixed L2 `1e-4`); and
- small MLP: input -> 128 ReLU -> 128 ReLU -> 3, AdamW `1e-3`, weight decay
  `1e-4`, MSE, 300 epochs, early stopping on validation MSE (patience 30).

The MLP initialization seeds are 11/22/33. Standardization uses training rows
only. The linear probe is deterministic and reported once; every MLP seed and
every shuffled-control combination is reported.

## Metrics and locked gate

Report final-test vector MSE, cosine similarity, correct-direction rates
(`cos > 0`, `cos > 0.5`), projected progress (`prediction · y`), and magnitude
error. Report mean ± population standard deviation over MLP seeds (and B3
shuffle seeds). No model or seed is selected using final test.

Stage 21A supports incremental Cartesian intent only if, for the MLP across all
three initialization seeds, B2 has simultaneously: at least 10% lower final
MSE, +0.05 higher mean cosine, and +0.05 higher correct-direction rate than
both B0 and the mean B3 control. Linear results are corroborative, not a way to
override this gate. Otherwise report the negative conclusion verbatim.

## Resources and Stage 21B gate

Expected collection is roughly 0.5--0.75 RTX 4090 hours including load/warm-up;
training is small and runs only after the pi05 server is SIGTERM-stopped. All
GPU server runs start with GPU/disk preflight and a separate no-control warm-up,
then end by SIGTERM-ing only that server and rechecking GPU/disk. Stage 21B is
permitted only if the locked gate above passes. Any later sequence model needs
a separately pre-registered training distribution and independent final test.
