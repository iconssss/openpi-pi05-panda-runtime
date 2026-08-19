# Project 2 Interview Guide

## Three-minute version

I built a safety-bounded remote runtime around the official OpenPI π0.5 DROID
policy and evaluated it on a Panda MuJoCo reach task. The key design decision
was that the policy server never controlled the robot directly: my runtime
owned typed observations, a process-owned five-second deadline, safe hold,
action-chunk execution, an explicit DROID 8-D to Panda bridge, limits, and
re-observation.

The systems path was reliable, so I tested the actual transfer claim rather
than treating valid actions as success. Frozen π0.5 reached 0/5 Panda targets.
I then ran preregistered one-step diagnosis and three frozen residual adapters:
adapters lowered final distance but all held-out episodes remained 0/24. To
avoid blaming the simulator controller, I independently validated the analytic
DLS velocity contract at 4/4 on a new final split.

Finally I asked whether final DROID actions carried task intent beyond Panda
state. A first target-level probe had concentrated directions, so I built a
same-state, balanced ±X/±Y/±Z counterfactual benchmark. On 480 frozen requests,
real actions did not beat state-only or shuffled controls. I froze the research
line. An attempted upstream-latent check stopped before evaluation because the
instrumentation altered action semantics. The project demonstrates reliable VLA
systems engineering and rigorous failure attribution, not real-robot or
zero-shot Panda capability.

## Ten-minute technical deep dive

### 1. Runtime contract (about 2 minutes)

The DROID-facing policy emits an `H x 8` chunk: seven arm values plus gripper.
The robot-side side owns `k`, the number of actions executed before a fresh
observation. I validate finite shapes, use a process-owned WebSocket transport
to make an unconfirmed call killable, enter a traceable safe hold on policy or
adapter failure, and reconnect before trusting a later response. The bridge
maps the declared DROID-like action convention into Panda commands with joint
limits. This avoids a dangerous hidden assumption that server output is an
actuator command.

### 2. Test the claim, not the plumbing (about 2 minutes)

Stable requests alone are not transfer. Stage 15 uses an independent 4-cm
geometric success metric and IK-reachable targets. The policy path is stable,
but reach is 0/5. Stage 17 tests fixed action interpretations one step at a
time: identity has weak directionality, yet only millimetre-scale improvement.
That explains why it was worth a bounded adapter study but does not reverse the
long-horizon result.

### 3. Adapter and control isolation (about 2 minutes)

Stage 18 trains residual adapters only on diagnostic-target data and evaluates
every seed on a fixed held-out target/visual grid. Final distance improves from
0.17973 m to roughly 0.102 m but success is 0/24 for every seed. Stage 19
reports late-horizon regression instead of inventing a causal story from
unlogged residuals or state shift. Stage 20B then uses an independent split:
analytic DLS and direct IK both reach 4/4. That means the tested low-level
Panda velocity contract is feasible in simulation; it does not prove anything
about π0.5.

### 4. Information and benchmark design (about 2 minutes)

Stage 21A's high cosine was misleading because labels were concentrated; a
constant direction did well. I audited state-target leakage and then replaced
the benchmark with Stage 22: each group has an exactly identical state paired
with six opposing target directions and four non-semantic visual realizations.
The test compares state-only, final action, and shuffled action. On held-out
groups, action plus state did not cross its prespecified six-way, opposite-pair,
and cosine margins.

### 5. Why stopping is part of the work (about 2 minutes)

Stage 23 permitted one latent side-channel check. It produced finite features,
but it changed the action feature by 0.00378194 when the tolerance was 1e-5.
Because the instrumentation was not observational, collecting 480 latents
would have confounded the result. I stopped, recorded an instrumentation
validity failure, and froze the line rather than treating “more layers” as a
research plan.

## Likely interview questions and short answers

1. **Why use a remote server?** It makes ownership and failure boundaries
explicit: inference is remote, but robot validation, timeout and execution stay
local to the runtime.
2. **Why is a thread timeout insufficient?** A timed-out thread can leave a
socket/request alive, so a later response may be stale. The process owner can
be terminated and recreated.
3. **What does safe hold mean here?** A traceable software state that stops new
commands after an untrusted policy/adapter path failure; it is not hardware E-stop certification.
4. **Why execute only first actions?** Action horizon is model output; execution
horizon is a robot-safety decision. Re-observation limits open-loop drift.
5. **Why not simply negate or rescale DROID actions?** Stage 17 preregistered
fixed alternatives; identity had the only weak directional evidence, but none
produced long-horizon success.
6. **Why did residual distance improve but success stay zero?** Progress toward
the target and sustained convergence across a 4-cm threshold are different
claims; curves show late regression.
7. **How did you prevent held-out seed picking?** All three seeds and the raw
baseline were reported; held-out targets/visuals never selected a seed or retraining.
8. **Why is DLS not a learned baseline?** It uses current simulator geometry and
analytic Jacobians, so it is a reachability/control reference only.
9. **What did Stage 20B isolate?** A specific analytic Panda velocity contract
can reach independently selected simulator targets; it removes one low-level
explanation, not the transfer limitation.
10. **Why wasn't Stage 21A enough?** Its direction distribution was concentrated;
a constant label direction achieved high cosine, reducing metric discrimination.
11. **How does Stage 22 avoid state shortcuts?** Six conditions share identical
proprioception within a group; whole groups—not rows—are assigned to splits.
12. **Why include shuffled actions?** It tests whether an apparent gain needs
the actual action-feature pairing rather than capacity or accidental correlation.
13. **What did Stage 22 show?** Final DROID actions did not provide locked,
held-out incremental intent above state-only and shuffled controls.
14. **Did you prove π0.5 lacks task semantics?** No. I only tested final action
features; the upstream instrumentation test was invalid before evaluation.
15. **Why not fix Stage 23 instrumentation and retry?** The published stop
boundary forbids repeated feature/layer redesign after a validity failure.
16. **Why is stopping valuable?** It prevents a portfolio from converting a
falsifiable hypothesis into unlimited tuning; the boundary is reproducible evidence.
17. **What was the most difficult engineering issue?** Making deadline behavior
truthful around the official synchronous WebSocket client without stale requests.
18. **What would hardware deployment require?** A reviewed robot SDK, calibrated
cameras, coordinate/unit validation, hardware limits, monitoring and safety approval.
19. **What does this add beyond an API demo?** It measures task success,
baselines, held-out splits and failure modes instead of equating a returned tensor with control.
20. **What is next?** A separate Project 3 trains a learned visual manipulation
policy with explicit held-out success rate, rather than continuing this frozen transfer path.
21. **Why not fine-tune π0.5 on DLS data?** That would demonstrate at most
simulator target-embodiment adaptation and risks obscuring the original frozen-transfer conclusion.
22. **How do you discuss negative results positively?** I state the supported
boundary first, then show which alternative explanations were ruled out and what remains unidentifiable.
