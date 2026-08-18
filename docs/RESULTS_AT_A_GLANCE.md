# Results at a glance

| Stage | Evidence | Result |
| --- | --- | --- |
| 3--7 | Official π0.5 client/server and fault boundaries | Live protocol, safe hold and process-owned reconnection validated. |
| 10 | First Panda live-policy smoke | Warm response H=15; first action executed once in MuJoCo. |
| 11 | Re-observation loop | 5/5 replans completed; cycles 1--4 mean RTT 81.10 ms. |
| 12 | Long stress run | 200/200 synthetic-input cycles; RTT mean/p95 82.61/88.15 ms; 0 safe holds. |
| 14 | Independent task validation | Zero/random fail; DLS IK oracle succeeds at 3.23 cm <= 4 cm. |
| 15 | π0.5 task-path suite | 200 requests, 0 safety failures, 0/5 reach successes. |

The Stage 15 result is intentional evidence of a transfer limitation, not a
system failure. See [Stage 16](STAGE_16_INTERVIEW_PACKAGE.md) for the narrative
and presentation boundaries.
