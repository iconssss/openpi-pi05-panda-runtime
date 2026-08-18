"""Receding-horizon execution: observe -> predict H -> execute first k -> repeat."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter

from .adapters import MockDroidAdapter
from .contracts import DROID_LIKE_ACTION_DIM, PolicyResponse
from .policy import PolicyClient
from .safety import DroidLikeSafetyFilter
from .simulation import MockDroidRobot


@dataclass(frozen=True)
class RuntimeConfig:
    execution_horizon: int
    expected_action_dim: int = DROID_LIKE_ACTION_DIM

    def __post_init__(self) -> None:
        if self.execution_horizon < 1:
            raise ValueError("execution_horizon must be at least 1.")


@dataclass
class RuntimeMetrics:
    policy_requests: int = 0
    executed_actions: int = 0
    clipped_actions: int = 0
    client_round_trip_ms: list[float] = field(default_factory=list)
    server_infer_ms: list[float] = field(default_factory=list)
    policy_infer_ms: list[float] = field(default_factory=list)
    safe_holds: int = 0
    termination_reason: str | None = None


class ClosedLoopRuntime:
    """Owns execution; a policy server never directly controls the robot."""

    def __init__(
        self,
        *,
        robot: MockDroidRobot,
        policy_client: PolicyClient,
        adapter: MockDroidAdapter | None = None,
        safety_filter: DroidLikeSafetyFilter | None = None,
        config: RuntimeConfig,
    ) -> None:
        self.robot = robot
        self.policy_client = policy_client
        self.adapter = adapter or MockDroidAdapter()
        self.safety_filter = safety_filter or DroidLikeSafetyFilter()
        self.config = config
        self.metrics = RuntimeMetrics()

    def run(self, *, prompt: str, max_execution_steps: int) -> RuntimeMetrics:
        completed = 0
        while completed < max_execution_steps:
            try:
                response = self._request_policy(prompt=prompt, step_index=completed)
                response.action_chunk.validate(expected_action_dim=self.config.expected_action_dim)
            except Exception as error:
                return self._fail_safe_hold(error)
            actions_to_execute = min(
                self.config.execution_horizon,
                response.action_chunk.horizon,
                max_execution_steps - completed,
            )
            for action in response.action_chunk.actions[:actions_to_execute]:
                try:
                    command = self.adapter.to_command(action)
                    safe_command = self.safety_filter.apply(command)
                except Exception as error:
                    return self._fail_safe_hold(error)
                self.robot.execute(safe_command.command)
                self.metrics.executed_actions += 1
                self.metrics.clipped_actions += int(safe_command.clipped)
                completed += 1
        return self.metrics

    def _fail_safe_hold(self, error: Exception) -> RuntimeMetrics:
        """Stop this run before an unconfirmed action can reach execution."""

        reason = f"{type(error).__name__}: {error}"
        self.robot.safe_hold(reason=reason)
        self.metrics.safe_holds += 1
        self.metrics.termination_reason = reason
        return self.metrics

    def _request_policy(self, *, prompt: str, step_index: int) -> PolicyResponse:
        observation = self.robot.observe(prompt=prompt, step_index=step_index)
        request_start = perf_counter()
        response = self.policy_client.infer(observation)
        self.metrics.client_round_trip_ms.append((perf_counter() - request_start) * 1000)
        self.metrics.policy_requests += 1
        if response.server_infer_ms is not None:
            self.metrics.server_infer_ms.append(response.server_infer_ms)
        if response.policy_infer_ms is not None:
            self.metrics.policy_infer_ms.append(response.policy_infer_ms)
        return response
