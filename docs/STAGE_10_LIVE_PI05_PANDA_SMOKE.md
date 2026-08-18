# Stage 10 - Live π0.5 Panda interface smoke

Date: 2026-08-18

## Claim boundary

This is one live `pi05_droid` policy request through the official OpenPI
WebSocket server, using synthetic Panda free-camera proxies. It validates an
end-to-end *software interface* path:

```text
Panda MuJoCo state + synthetic camera proxies
  -> typed DROID request
  -> process-owned WebSocket client (5 s deadline)
  -> official pi05_droid server
  -> H=15, 8-D action chunk
  -> Panda bridge safety limits
  -> execute first action only in MuJoCo
```

It does not establish visual understanding, cross-embodiment policy transfer,
task completion, camera calibration, or real-robot safety.

## Cold-start behavior

The first no-control warm-up request took 33,203.53 ms end-to-end
(`policy_infer_ms=32,525.47`). A prior direct request with a 5 s deadline safely
held rather than executing because this first compilation exceeded its deadline.
This is the desired behavior: an unconfirmed request must not result in a
simulator command. Warm-up evidence is
`/root/shared-nvme/openpi-robot-runtime/results/pi05_panda_warmup.json`.

## Warm live smoke

After warm-up, a process-owned client with a 5 s deadline completed one Panda
request in 211.33 ms. Server inference was 98.86 ms and policy inference 60.12
ms. The returned chunk had horizon 15; only row 0 was converted and executed
for 15 MuJoCo simulation steps. The bridge limited at least one target to the
Panda XML joint bounds (`bridge_clipped=true`).

Result artifact:

- `/root/shared-nvme/openpi-robot-runtime/results/pi05_panda_smoke/report.json`

The policy server was SIGTERM-stopped immediately after collection. Post-run
GPU state was 0% utilization and 1 MiB allocated.

## Engineering takeaway

There are two distinct latency regimes: a cold model/request phase that needs a
controlled warm-up while the simulator remains held, and a warm phase where a
hard process-owned deadline is practical. Any future multi-step simulation
experiment must warm the server before it enables execution and must retain the
same safe-hold rule on timeout.
