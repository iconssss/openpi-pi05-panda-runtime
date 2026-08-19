# Project 2 — Core Results

This table intentionally contains only the evidence that determines the final
claim. Detailed stage-by-stage protocols remain linked from the README.

| Decision question | Locked evidence | Result | Consequence |
| --- | --- | --- | --- |
| Is the remote VLA runtime usable as a bounded software path? | Official π0.5 checkpoint/server; process-owned 5-s deadline; 200-request stress | Valid request/action path; 0 safe holds in stress; warm RTT mean/p95 82.61/88.15 ms | Runtime/safety engineering is demonstrated. |
| Does frozen DROID action zero-shot transfer to Panda reach? | Five IK-reachable targets, 200 policy requests | 0/5 reach success | No zero-shot Panda-skill claim. |
| Does a frozen residual action adapter solve it? | Three diagnostic-trained seeds; fixed 4-target × 6-visual held-out set; 40 steps | All arms 0/24 success. Mean final distance: raw 0.17973 m; adapters 0.10159–0.10519 m | Distance reduction is not task success. |
| Is the low-level Panda velocity contract itself infeasible? | Stage 20B new split, analytic DLS and direct IK | DLS 4/4 at 3.87 cm; direct IK 4/4 | The tested simulator control contract is feasible; this is not a VLA result. |
| Does final π0.5 DROID action add transferable Cartesian intent? | Stage 22 exact-same-state, balanced ±X/±Y/±Z groups; 480 frozen requests | State+real action does not beat state-only or shuffled control on held-out six-way/pair metrics | Sequence adapter is blocked. |
| Do upstream latents answer the remaining semantic question? | Stage 23 action-equivalence preflight | Instrumentation changed action feature by 0.00378194 > 1e-5; no full extraction | Instrumentation validity failure, not a latent negative result. |

## Final interpretation

Project 2 proves a safe remote-inference and cross-embodiment evaluation
workflow, not a successful transferred Panda policy. The frozen π0.5→Panda
research path is closed by a pre-registered stop rule. No real-robot,
calibration, sim-to-real, safety-certification, or upstream-semantic claim is
made.
