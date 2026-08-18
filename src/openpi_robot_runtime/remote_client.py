"""Bounded robot-side remote-policy boundary.

The official OpenPI client is intentionally minimal and retries connection
forever. This wrapper defines the behavior required by a robot runtime: calls
must be bounded, classified, and safe to turn into a hold/stop decision.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from multiprocessing import get_context
from multiprocessing.context import BaseContext
from queue import Empty
from time import perf_counter
from typing import Callable, Protocol


class RemotePolicyError(RuntimeError):
    """A transport, protocol, or policy-server failure."""


class RemotePolicyTimeout(RemotePolicyError):
    """A policy response did not arrive within the robot-side deadline."""


class OpenPITransport(Protocol):
    """Structural interface satisfied later by the official WebsocketClientPolicy."""

    def infer(self, observation: dict[str, object]) -> dict[str, object]:
        """Send one request and return one decoded OpenPI response."""


@dataclass(frozen=True)
class TimedResponse:
    payload: dict[str, object]
    client_round_trip_ms: float


class BoundedRemotePolicyClient:
    """Adds a deadline to a synchronous OpenPI-compatible transport.

    A timeout does not imply that an already-sent remote request was cancelled.
    The caller must transition the robot to safe hold and reconnect before a
    later request is trusted.
    """

    def __init__(self, transport: OpenPITransport, *, timeout_seconds: float) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive.")
        self._transport = transport
        self._timeout_seconds = timeout_seconds

    def infer(self, observation: dict[str, object]) -> TimedResponse:
        start = perf_counter()
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(self._transport.infer, observation)
        try:
            payload = future.result(timeout=self._timeout_seconds)
        except FutureTimeoutError as error:
            future.cancel()
            raise RemotePolicyTimeout(f"Policy request exceeded {self._timeout_seconds:.3f}s.") from error
        except Exception as error:
            raise RemotePolicyError("Policy request failed.") from error
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
        if not isinstance(payload, dict):
            raise RemotePolicyError("Policy response is not a dictionary.")
        return TimedResponse(payload=payload, client_round_trip_ms=(perf_counter() - start) * 1000)


@dataclass(frozen=True)
class OpenPIWebsocketTransportFactory:
    """Pickle-safe factory; imports the optional official client in its worker."""

    host: str
    port: int

    def __call__(self) -> OpenPITransport:
        from openpi_client.websocket_client_policy import WebsocketClientPolicy

        return WebsocketClientPolicy(host=self.host, port=self.port)


def _process_transport_worker(
    factory: Callable[[], OpenPITransport], request_queue: object, response_queue: object
) -> None:
    """Own transport construction and every send/receive in one child process."""

    try:
        transport = factory()
    except BaseException as error:
        response_queue.put(("startup_error", f"{type(error).__name__}: {error}"))  # type: ignore[attr-defined]
        return
    response_queue.put(("ready",))  # type: ignore[attr-defined]
    while True:
        message = request_queue.get()  # type: ignore[attr-defined]
        if message == ("close",):
            return
        request_id, observation = message
        try:
            response_queue.put(("response", request_id, transport.infer(observation)))  # type: ignore[attr-defined]
        except BaseException as error:
            response_queue.put(("error", request_id, f"{type(error).__name__}: {error}"))  # type: ignore[attr-defined]


class ProcessOwnedTransport:
    """A deadline-capable transport whose socket stays inside one child process.

    On an unconfirmed request the process is terminated and the instance is
    closed. The caller must safe-hold, then explicitly call :meth:`reconnect`
    before trusting another response. This avoids the stale-response ambiguity
    of a background thread that remains blocked on ``recv``.
    """

    def __init__(
        self,
        factory: Callable[[], OpenPITransport],
        *,
        request_timeout_seconds: float,
        startup_timeout_seconds: float = 10.0,
        start_method: str | None = None,
    ) -> None:
        if request_timeout_seconds <= 0 or startup_timeout_seconds <= 0:
            raise ValueError("Process transport timeouts must be positive.")
        self._factory = factory
        self._request_timeout_seconds = request_timeout_seconds
        self._startup_timeout_seconds = startup_timeout_seconds
        # Use the platform default (fork on the remote Ubuntu container, spawn
        # on Windows). The transport itself is always constructed in the child.
        self._context: BaseContext = get_context(start_method)
        self._process = None
        self._request_queue = None
        self._response_queue = None
        self._next_request_id = 0

    def infer(self, observation: dict[str, object]) -> dict[str, object]:
        self._ensure_worker()
        assert self._request_queue is not None
        assert self._response_queue is not None
        self._next_request_id += 1
        request_id = self._next_request_id
        self._request_queue.put((request_id, observation))
        try:
            kind, received_id, payload = self._response_queue.get(timeout=self._request_timeout_seconds)
        except Empty as error:
            self.close(force=True)
            raise RemotePolicyTimeout(
                f"Process-owned policy request exceeded {self._request_timeout_seconds:.3f}s; worker terminated."
            ) from error
        if received_id != request_id:
            self.close(force=True)
            raise RemotePolicyError("Received a stale or mismatched policy response; worker terminated.")
        if kind == "error":
            raise RemotePolicyError(f"Policy worker failed: {payload}")
        if kind != "response" or not isinstance(payload, dict):
            raise RemotePolicyError("Policy worker returned an invalid response.")
        return payload

    def reconnect(self) -> None:
        """Discard any prior worker; a new connection is created on next infer."""

        self.close(force=True)

    def close(self, *, force: bool = False) -> None:
        if self._process is None:
            return
        if self._process.is_alive() and not force:
            self._request_queue.put(("close",))
            self._process.join(timeout=0.5)
        if self._process.is_alive():
            self._process.terminate()
            self._process.join(timeout=1.0)
        self._process = None
        for queue in (self._request_queue, self._response_queue):
            queue.close()
        self._request_queue = None
        self._response_queue = None

    def _ensure_worker(self) -> None:
        if self._process is not None and self._process.is_alive():
            return
        self.close(force=True)
        self._request_queue = self._context.Queue()
        self._response_queue = self._context.Queue()
        self._process = self._context.Process(
            target=_process_transport_worker,
            args=(self._factory, self._request_queue, self._response_queue),
            daemon=True,
        )
        self._process.start()
        try:
            startup = self._response_queue.get(timeout=self._startup_timeout_seconds)
        except Empty as error:
            self.close(force=True)
            raise RemotePolicyTimeout(
                f"Policy worker did not establish a connection within {self._startup_timeout_seconds:.3f}s."
            ) from error
        if startup[0] != "ready":
            self.close(force=True)
            detail = startup[1] if len(startup) > 1 else "unknown startup failure"
            raise RemotePolicyError(f"Policy worker failed to start: {detail}")
