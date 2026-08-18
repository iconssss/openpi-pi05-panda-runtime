# Stage 7 — Process-Owned Deadline Transport

Date: 2026-08-18

`ProcessOwnedTransport` constructs the official synchronous WebSocket client in
a child process. The parent applies a response deadline; an unconfirmed request
terminates that child and is never reused. Recovery requires a new child and a
new WebSocket, avoiding stale-response ambiguity.

No package was installed: this uses Python `multiprocessing`; the optional
OpenPI-client import happens only inside the child.

Remote RTX 4090 validation passed three cases: a normal response returned
horizon 15; a 1-ms deadline produced one safe hold and zero mock commands; a
fresh process then reconnected and returned horizon 15. Artifact:
`/root/shared-nvme/openpi-robot-runtime/results/process_transport_deadline.json`.

Compatibility note: on the remote Ubuntu host, forced `spawn` connected but
hung before sending inference. The platform-default `fork` model passed while
still constructing the WebSocket in the child. The implementation therefore
uses the platform default unless overridden.

Scope remains static frames and MockDroidRobot; no physical hardware claim.
