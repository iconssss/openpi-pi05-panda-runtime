# Results at a glance

| Stage | Evidence | Result |
| --- | --- | --- |
| 3--7 | Official π0.5 client/server and fault boundaries | Live protocol, safe hold and process-owned reconnection validated. |
| 10 | First Panda live-policy smoke | Warm response H=15; first action executed once in MuJoCo. |
| 11 | Re-observation loop | 5/5 replans completed; cycles 1--4 mean RTT 81.10 ms. |
| 12 | Long stress run | 200/200 synthetic-input cycles; RTT mean/p95 82.61/88.15 ms; 0 safe holds. |
| 14 | Independent task validation | Zero/random fail; DLS IK oracle succeeds at 3.23 cm <= 4 cm. |
| 15 | π0.5 task-path suite | 200 requests, 0 safety failures, 0/5 reach successes. |
| 17 | Pre-registered embodiment-mismatch diagnosis | 72/72 requests, 0 safe holds; identity mapping gives small one-step progress but no long-horizon success claim. |
| 18 | Frozen residual-adapter held-out evaluation | All arms 0/24 success at 4 cm; adapters reduce mean final distance from 0.17973 m (raw) to 0.10159--0.10519 m, without seed selection. |
| 19 | Read-only multi-step failure analysis | Curves show adapter/DLS initial improvement followed by late-horizon stall/drift; zero clips/safe holds, while residual/state-shift attribution is not identifiable from Stage 18 logs. |
| 20 | Independent CPU-only control feasibility ladder | Direct-position IK 4/4, but diagnostic-selected DLS bridge only 3/4 on one final-test run; bridge/time contract not proven feasible, independent of pi05. |
| 20B | Independent low-level contract replication | New-split, diagnostic-frozen DLS bridge reaches 4/4 final targets (3.87 cm mean); proves only this analytic simulator contract, not pi05 transfer. |
| 21A | Frozen Cartesian intent probe | No state→target-ID leakage found, but state+real π0.5 fails to beat state-only; concentrated direction labels limit cosine, so Stage 21B is blocked. |
| 22 | Counterfactual benchmark CPU validation | Exact state-matched ±axis pairs yield constant cosine 0 and state-only task-condition chance 1/6; no π0.5 collection yet. |

The Stage 15 result is intentional evidence of a transfer limitation, not a
system failure. Stage 17 narrows the failure mechanism without changing that
conclusion. See [Stage 16](STAGE_16_INTERVIEW_PACKAGE.md) for the narrative and
presentation boundaries.
