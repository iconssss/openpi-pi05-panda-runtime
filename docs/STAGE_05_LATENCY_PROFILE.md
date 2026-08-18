# Stage 5 — π0.5 Inference Service Latency Profile

Date: 2026-08-18

## Setup

- Official verified `pi05_droid` checkpoint on remote RTX 4090.
- One official synchronous WebSocket connection to the local policy server.
- Three warmup requests, then 60 sequential measured DROID-schema requests.
- Three fixed text prompts, static zero `224x224x3` RGB frames, fixed robot
  state. This is service profiling only, not a robot-task benchmark.

## Results

| Metric | Mean | Median | p95 | Range |
| --- | ---: | ---: | ---: | ---: |
| Client round trip | 78.54 ms | 77.86 ms | 81.49 ms | 76.64–88.16 ms |
| Server inference | 77.75 ms | 77.10 ms | 80.61 ms | 76.02–87.16 ms |
| Policy inference | 55.79 ms | 55.76 ms | 56.15 ms | 55.35–56.23 ms |

The policy's internal inference is stable in this controlled setting. The
roughly 22 ms difference between policy inference and end-to-end client time
includes server-side processing, serialization, and local WebSocket overhead.
This is an inference from the measured timing fields, not a direct component
breakdown.

GPU sampling saved 368 samples at 100 ms intervals. During active requests it
reached 79–81% utilization, about 20.9 GB model memory, and about 267–269 W.
Idle samples were retained in the same CSV, so no mean-utilization claim is
made from the mixed load/idle trace.

## Artifacts and limits

- Result JSON: `/root/shared-nvme/openpi-robot-runtime/results/pi05_droid_latency_profile.json`
- GPU samples: `/root/shared-nvme/openpi-robot-runtime/results/pi05_droid_latency_profile_gpu.csv`
- Log: `/root/shared-nvme/openpi-robot-runtime/logs/pi05_droid_latency_profile.log`

Different prompts produced different first action vectors, demonstrating that
language reaches the policy request. Static zero images and a fixed state mean
this does not demonstrate semantic understanding, visual grounding,
manipulation success, or physical robot safety.

The server was stopped via SIGTERM after collection; the final GPU check was
0% utilization and 1 MiB allocated.
