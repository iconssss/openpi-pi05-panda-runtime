# Stage 13 - Latency and safety analysis

Stage 10--12 remote result JSON was consolidated without loading the policy or
using the GPU. The local D-drive artifacts are:

- [`summary.md`](../artifacts/stage13/summary.md)
- [`summary.json`](../artifacts/stage13/summary.json)
- [`latency_safety_summary.svg`](../artifacts/stage13/latency_safety_summary.svg)

## Evidence summary

| Measurement | Result |
| --- | ---: |
| Cold no-control warm-up | 33,923.64 ms |
| Warm single Panda request | 211.33 ms |
| Stage 11 steady cycles 1--4 mean | 81.10 ms |
| Stage 12, 200 requests mean / p95 | 82.61 / 88.15 ms |

The cold phase is incompatible with a 5-second execution deadline. It triggered
one documented safe-hold and zero Panda actions, demonstrating that policy
warm-up must precede control enablement. After warm-up, all 200 synthetic-input
stress cycles completed without safe holds.

This analysis is intentionally not a Panda skill, task success, real-camera
robustness, or cross-embodiment-transfer result. Its contribution is evidence
for a bounded, observable VLA-to-simulator runtime path.
