# Stage 22 - Pre-registered Counterfactual Task-Conditioned Cartesian Intent Benchmark

## Question

For identical Panda proprioceptive states, do frozen pi05 outputs encode which
visual/prompt task condition requires motion in one of six opposing Cartesian
directions, beyond state-only and shuffled-action controls? This document and
the initial artifact are CPU-only benchmark validation only: no pi05 request,
adapter training, or model fitting is authorized yet.

## Counterfactual construction and source

Twenty deterministic state groups (seed `20260822`) contain seven Panda joint
positions and gripper state. Each group produces six task conditions with the
**identical** proprioceptive state and labels/target offsets `+X,-X,+Y,-Y,+Z,-Z`
at 10 cm. The eventual MuJoCo scene will render its target and use a fixed
prompt that names the visible colored target/task condition; no Cartesian
coordinate is provided to a probe. The two DROID images and prompt are the
only task-conditioned source for frozen pi05.

Groups 0--11 train, 12--15 validation, 16--19 final test. A whole six-condition
counterfactual group is inseparable: no group, state, paired target or episode
crosses splits. A formal collection, if authorized later, will use four
independent visual realizations per condition (480 frozen requests), retaining
group/episode ID and visual condition only outside Git.

## Labels, prohibited fields, and controls

Primary label is normalized Cartesian translation intent, exactly the six unit
axis directions. Magnitude (0.10 m) is secondary. Target pose/coordinates,
Cartesian error, DLS/IK values, target ID, future state/action, success, and
any goal-derived field are forbidden probe inputs.

Baselines are constant direction, state-only, pi05-only, state+real pi05,
state+training-shuffled pi05, and optional visual/prompt-only (which still may
not receive explicit coordinates). Linear and small MLP probes use target/group
level splits, training-only normalization, three initialization seeds, and
three training-shuffle seeds.

## Pre-collection benchmark gates

Each split must contain equal counts of all six directions. The constant
direction baseline's held-out cosine must be at most 0.10 in absolute value.
Within each counterfactual group, max proprioceptive-state difference must be
zero (floating tolerance `1e-12`); state-only task-condition identification is
therefore limited to 1/6 chance. A nearest-neighbor task-condition audit must
not exceed 1/6 + 0.05. Failure of any gate blocks pi05 collection.

Primary final metric is per-pair discrimination accuracy: for every opposing
pair at one state, both predicted directions must have positive cosine to their
own label and negative cosine to the counterpart label. Also report MSE,
cosine, six-way direction classification, and real-vs-shuffled improvement.

Stage 22 may support incremental task-conditioned intent only if held-out
state+real pi05 exceeds both state-only and shuffled controls by at least 10
percentage points in pair discrimination and six-way accuracy, and by at least
0.05 cosine, consistently over all MLP seeds. Otherwise sequence-aware adapter
work remains blocked. Any future collection/server use needs a separately
reviewed execution approval after these CPU gates pass.

## Frozen-collection task-condition audit and pilot gate

Before the authorized frozen collection, a CPU/MuJoCo task-condition audit
will render a small deterministic subset. For each group its six target
positions must equal the corresponding `+X,-X,+Y,-Y,+Z,-Z` 10-cm teacher
offset from the shared end-effector state (position error at most `1e-12`), and
their rendered images must have six distinct pixel hashes. The seven joints
and gripper are generated once per group and reused bit-for-bit for all 24
condition/visual rows. Thus direction is supplied only by the target's visual
location; all four visual realizations change only camera/texture/appearance
factors and retain the same target offset and teacher label.

The fixed collection prompt is: "Move the Panda end effector to the visible
target safely in simulation." It is identical for all conditions and may not
contain direction names, signed-axis strings, Cartesian-coordinate wording,
numeric coordinates, or an equivalent task label. The downstream probe feature
schema is fixed to Panda proprioceptive state and the frozen pi05 action feature
only. It never receives target coordinates, direction/group identifiers, prompt
tokens, pixels, image hashes, or visual-condition IDs.

One group with one canonical visual realization is first sent to the frozen
server (six requests). Collection proceeds only if all six responses are
safe/nonempty and the maximum pairwise L2 difference between first actions is
greater than `1e-4`; otherwise the observation/prompt path is diagnosed before
any 480-request run. This pilot threshold is an input-path gate, not a model
quality metric. The full run is exactly 20 groups x 6 directions x 4 visual
realizations = 480 requests, with the model and all protocol thresholds frozen.
