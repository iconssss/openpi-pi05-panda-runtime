"""Policy boundary: fake now, official WebSocket client in the next stage."""

from __future__ import annotations

from typing import Protocol

from .contracts import Observation, PolicyResponse


class PolicyClient(Protocol):
    def infer(self, observation: Observation) -> PolicyResponse:
        """Return one fresh predicted action chunk for this observation."""


class DeterministicFakePolicyClient:
    """CPU-only policy double whose outputs deliberately exercise safety clipping."""

    def __init__(self, response: PolicyResponse) -> None:
        self._response = response
        self.requests: list[Observation] = []

    def infer(self, observation: Observation) -> PolicyResponse:
        self.requests.append(observation)
        return self._response

