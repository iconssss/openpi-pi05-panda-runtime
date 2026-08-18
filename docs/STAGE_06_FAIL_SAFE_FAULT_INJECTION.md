# Stage 6 — Fail-Safe Fault Injection

Date: 2026-08-18

## Why this matters

A policy-server integration is incomplete if it only shows successful tensor
returns. The runtime must make an explicit decision when a policy reply is not
confirmed: it must not execute a guessed, stale, or absent action.

## Implementation

- `ClosedLoopRuntime` now catches policy-response, action-shape, adapter, and
  safety-filter exceptions before an affected action reaches execution.
- It calls `safe_hold(reason=...)`, increments `safe_holds`, records a
  termination reason, and ends this run.
- `MockDroidRobot.safe_hold` is a traceable no-motion mock operation. A real
  robot must replace it with a separately reviewed SDK/emergency-control action.

## Remote controlled test

The test used the official local π0.5 DROID server and static test frames.
The first policy request was real. Before the second request, a wrapper raised
a deliberate `ConnectionError`; it did not disrupt the server or any hardware.

| Check | Result |
| --- | --- |
| Confirmed real policy response and mock execution | 1 |
| Controlled policy attempts | 2 |
| Further mock commands after fault | 0 |
| Recorded safe holds | 1 |
| Outcome | pass |

Artifact:
`/root/shared-nvme/openpi-robot-runtime/results/policy_fault_injection.json`.

## Remaining production gap

The official synchronous client must remain on its owning thread. Therefore,
the current thread-confined compatibility mode does not create a hard,
externally cancellable deadline for an unresponsive socket. The safe-hold logic
is verified for classified errors; the next production-grade increment is a
dedicated process-owned transport that can terminate/reconnect a stuck request
and then report the same safe hold. That should be evaluated before any real
robot adapter is considered.
