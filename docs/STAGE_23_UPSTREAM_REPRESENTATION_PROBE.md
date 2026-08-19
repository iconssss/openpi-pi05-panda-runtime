# Stage 23 — Pre-registered Upstream Representation Transfer Feasibility

## Question

On Stage 22's fixed counterfactual groups, does a frozen upstream π0.5
representation contain held-out task-conditioned Cartesian direction
information that is absent from the final DROID action? This tests a
representation-stage hypothesis, not Panda control, fine-tuning, an adapter,
or real-robot capability.

## Source feasibility and fixed tap points

Read-only inspection of the installed official OpenPI source found:

- `src/openpi/models/pi0.py:embed_prefix` constructs image tokens using
  `PaliGemma.img`, language tokens using `PaliGemma.llm(..., method="embed")`,
  and obtains contextual `prefix_out` on the sampler's KV-cache fill pass.
- `sample_actions` repeatedly obtains action-expert `suffix_out`, applies
  `action_out_proj`, and returns only the final action. No documented public
  latent-return API exists.
- For the π0.5 branch, `embed_suffix` uses noisy action/time tokens with
  AdaRMS conditioning; it does not create the non-π0 state token. Therefore a
  state-conditioned latent must not be claimed without verifying an additional
  official observation path at extraction time.

The only permitted code change is a local, version-pinned optional
`return_features` instrumentation path that returns the already-computed
contextual prefix token sequence and final denoising-step action-expert token
sequence alongside the normal frozen action. It changes neither checkpoint
weights, normalization, sampler steps, action output, nor transport deadline.

Three fixed exported feature families are:

1. **VLM prefix:** mean-pool valid contextual `prefix_out` tokens.
2. **Action-expert:** mean-pool final-step `suffix_out` action-horizon tokens.
3. **Pre-output:** mean-pool the same final action-token hidden states before
   `action_out_proj` (reported separately only if it is not byte-identical to
   family 2 under the implementation).

Features are float16 plus a validity mask, pooled before storage; raw token
arrays, pixels, prompts, target positions, direction/group identifiers, and
KV caches are never probe inputs or public artifacts.

## Dataset, leakage controls, and extraction

Reuse Stage 22's immutable 20 groups, six directions, four visual
realizations, exact group-level train/validation/test split (12/4/4 groups),
neutral identical prompt, labels, success threshold, and task-condition audit.
No group/pair crosses splits. The extractor receives the normal policy
observation only. Each downstream probe receives exactly Panda state plus one
declared frozen feature family; it never receives target coordinates, direction
or group ID, prompt tokens, pixels, visual ID, teacher action, DLS/IK data,
future state/action, or a final success field.

Before full extraction, six canonical conditions of one group are sent through
a no-control warm-up/pilot. The exported action must equal the normal
instrumented-off action within `1e-5` max absolute error, all feature tensors
must be finite with nonzero variance, and at least one feature family's maximum
pairwise L2 across the six conditions must exceed `1e-4`. Otherwise stop and
diagnose instrumentation; do not run the full extraction.

The full extraction is one frozen forward per existing 480 observation. It may
emit action and features in the same sampler call, avoiding a second GPU pass.
Use the existing process-owned five-second deadline, first-action convention,
safe-hold logging, no-control warm-up, remote shared storage, and only SIGTERM
for the run-specific server. No control is executed.

## Baselines, models, metrics, and seeds

For each feature family, fit the locked Stage 22 linear ridge and small MLP
with: constant +X; state-only; final-action-only; state+final-action;
feature-only; state+real-feature; and state+training-shuffled-feature. Training
normalization is fit only on the 12 training groups. Use initialization seeds
11/22/33 and training-shuffle seeds 101/202/303. Retain Stage 22 cosine, MSE,
six-way accuracy, and within-group opposing-pair discrimination. Report every
seed and mean +/- population standard deviation; never select a seed on test.

## Locked success gate and interpretation

For at least one declared upstream family, across all three MLP seeds on the
held-out four groups, state+real-feature must exceed both state-only and
state+shuffled-feature by at least 0.10 in six-way accuracy and opposing-pair
discrimination, and 0.05 cosine. It must also exceed state+final-action by at
least 0.10 in both discrimination metrics. Linear evidence is corroborative.

If this gate passes, the limited conclusion is: **in this frozen Stage 22
simulator benchmark, task-conditioned information is measurable upstream but
not in the final DROID action feature.** It does not establish causal loss at a
specific layer, a learned Panda policy, real-robot capability, or justify an
adapter. If it fails, close π0.5→Panda adaptation under the strategic stop rule.

## Resource and stop boundary

Budget is at most 2 remaining 4090 GPU-hours and 2 GB persistent artifact
storage. No dependency, checkpoint download, weight update, adapter training,
or official fine-tuning is authorized. Any need for a larger feature dump,
longer execution, new dependency, or a second test collection stops for a new
decision. After the one extraction, SIGTERM the server and verify GPU/disk.
