# Stage 12 - 200-request Panda interface stress experiment

Date: 2026-08-18

## Design

This is a long-run systems stress measurement after the mandatory no-control
warm-up. It evaluates five deterministic synthetic-observation conditions, each
with 40 fresh render/request/first-action/physics cycles:

1. nominal free-camera proxies;
2. exterior camera azimuth +15 degrees;
3. exterior camera azimuth -15 degrees;
4. brightness gain 0.55;
5. RGB Gaussian noise with standard deviation 18.

The simulator starts every condition at the midpoint of each XML joint range so
the action bridge is tested from a valid pose, rather than conflating an invalid
default pose with policy behavior. Each request retains the process-owned 5 s
deadline; a condition would safe-hold and stop its own execution at the first
transport, protocol, or safety error.

## Result

- 200 / 200 requested replans completed.
- 0 / 5 conditions safe-held.
- 0 bridge clamps were needed from the valid midpoint initialization.
- Mean client round-trip time: **82.61 ms**; p95: **88.15 ms**.
- Mean server inference time: **79.81 ms**.
- Mean policy inference time: **56.41 ms**.
- Every cycle executed only action row zero and advanced 33 MuJoCo steps.

The policy server was stopped immediately after the experiment. Final GPU state
was 0% utilization and 1 MiB allocated; the shared disk retained 21 GB free.

## Interpretation limits

Completion means the deployed protocol, watchdog, observation builder, action
bridge, and simulator did not fail under these valid synthetic inputs. It does
not measure task reward, visual robustness in the real world, calibrated-camera
robustness, Panda skill, or cross-embodiment transfer.

Artifact: `/root/shared-nvme/openpi-robot-runtime/results/pi05_panda_stress/report.json`.
