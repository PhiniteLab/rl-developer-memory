from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(slots=True, frozen=True)
class EnvSpec:
    """Framework-agnostic environment specification."""

    env_id: str
    observation_shape: tuple[int, ...]
    action_shape: tuple[int, ...]
    action_low: float
    action_high: float
    reward_scale: float = 1.0
    max_episode_steps: int = 1
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class StepResult:
    """A single environment step."""

    observation: float
    reward: float
    terminated: bool
    truncated: bool
    info: dict[str, float | str]


class Environment(Protocol):
    """Minimal environment protocol consumed by the backbone."""

    spec: EnvSpec

    def reset(self) -> float:
        ...

    def step(self, action: float) -> StepResult:
        ...


class DeterministicBanditEnv:
    """A tiny deterministic control task used for tests and smoke runs.

    The environment emits a constant observation and rewards actions that move close to
    the configured target action. It is simple enough to keep the backbone dependency-free
    while still exercising training, evaluation, checkpointing, and theory bindings.
    """

    def __init__(self, *, target_action: float = 0.5, max_episode_steps: int = 4) -> None:
        self.spec = EnvSpec(
            env_id="deterministic-bandit-v0",
            observation_shape=(1,),
            action_shape=(1,),
            action_low=-1.0,
            action_high=1.0,
            reward_scale=1.0,
            max_episode_steps=max_episode_steps,
            metadata={"target_action": f"{target_action:.3f}"},
        )
        self.target_action = float(target_action)
        self._step = 0

    def reset(self) -> float:
        self._step = 0
        return 1.0

    def step(self, action: float) -> StepResult:
        self._step += 1
        bounded_action = max(self.spec.action_low, min(self.spec.action_high, float(action)))
        reward = self.spec.reward_scale * (1.0 - abs(bounded_action - self.target_action))
        terminated = self._step >= self.spec.max_episode_steps
        return StepResult(
            observation=1.0,
            reward=reward,
            terminated=terminated,
            truncated=False,
            info={"target_action": self.target_action, "action": bounded_action, "step": float(self._step)},
        )


class ActionClampWrapper:
    """Clamp actions to the declared action bounds."""

    def __init__(self, env: Environment) -> None:
        self.env = env
        self.spec = env.spec

    def reset(self) -> float:
        return self.env.reset()

    def step(self, action: float) -> StepResult:
        bounded_action = max(self.spec.action_low, min(self.spec.action_high, float(action)))
        result = self.env.step(bounded_action)
        result.info.setdefault("wrapper", "ActionClampWrapper")
        return result
