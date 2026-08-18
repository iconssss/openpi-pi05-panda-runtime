# Stage 15 - Live π0.5 Panda reach suite

## Protocol

Five static reach targets were generated from the same official Panda `home`
reset using small deterministic offsets. Each target was first prechecked by a
non-learned damped least-squares IK solver (all residuals <= 1.90 mm), then run
for 40 cycles with this constrained path:

```text
synthetic free-camera images + Panda joint state
  -> official pi05_droid server
  -> process-owned 5 s deadline
  -> first action only
  -> DROID-like Panda bridge + 33 MuJoCo steps
```

The server was warmed before execution. A transport error would safe-hold and
stop that target episode.

## Result

| Target | IK residual | Final distance | π0.5 bridge success |
| --- | ---: | ---: | --- |
| 0 | 1.90 mm | 18.18 cm | no |
| 1 | 0.19 mm | 18.35 cm | no |
| 2 | 0.02 mm | 17.60 cm | no |
| 3 | 0.60 mm | 19.14 cm | no |
| 4 | 0.10 mm | 17.44 cm | no |

All 200/200 policy requests completed; there were zero safe-hold episodes and
zero bridge clamps. Mean client RTT by target ranged from 83.03 to 89.67 ms.
No episode reached the 4-cm geometric threshold.

## Honest interpretation

This is a valuable negative result. It rules out the invalid claim that a
working DROID protocol + a dimensionally compatible Panda bridge automatically
creates Panda reaching skill. The target is geometrically reachable and the
system path is stable, yet the out-of-distribution synthetic Panda cameras,
state convention, and action semantics do not yield task success.

It does demonstrate reliable infrastructure under task-scene observations:
checkpoint/server warm-up, bounded WebSocket inference, fresh state/image
construction, first-action execution, and safe termination all completed.

Artifact: `/root/shared-nvme/openpi-robot-runtime/results/pi05_panda_reach_suite/report.json`.
The server was SIGTERM-stopped after collection; GPU returned to 0% / 1 MiB.

## Next technical direction

Improving this task score requires a matched embodiment/data solution, not
loosening safety limits or changing the success threshold: calibrated Panda
cameras, a Panda-compatible action representation, and demonstrations or
fine-tuning/evaluation data. Those are a separate research scope from the
current DROID-interface systems project.
