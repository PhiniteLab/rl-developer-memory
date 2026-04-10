from __future__ import annotations

import math
from dataclasses import dataclass, field
from random import Random
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


class StochasticBanditEnv:
    """Noisy version of the deterministic bandit — reward has Gaussian noise.

    Useful for testing whether agents handle stochastic rewards correctly
    and whether running statistics adapt to noise.
    """

    def __init__(
        self,
        *,
        target_action: float = 0.5,
        noise_std: float = 0.1,
        max_episode_steps: int = 4,
        seed: int = 42,
    ) -> None:
        self.spec = EnvSpec(
            env_id="stochastic-bandit-v0",
            observation_shape=(1,),
            action_shape=(1,),
            action_low=-1.0,
            action_high=1.0,
            reward_scale=1.0,
            max_episode_steps=max_episode_steps,
            metadata={"target_action": f"{target_action:.3f}", "noise_std": f"{noise_std:.3f}"},
        )
        self.target_action = float(target_action)
        self.noise_std = float(noise_std)
        self._rng = Random(seed)
        self._step = 0

    def reset(self) -> float:
        self._step = 0
        return 1.0

    def step(self, action: float) -> StepResult:
        self._step += 1
        bounded = max(self.spec.action_low, min(self.spec.action_high, float(action)))
        base_reward = self.spec.reward_scale * (1.0 - abs(bounded - self.target_action))
        noise = self._rng.gauss(0.0, self.noise_std)
        reward = base_reward + noise
        terminated = self._step >= self.spec.max_episode_steps
        return StepResult(
            observation=1.0,
            reward=reward,
            terminated=terminated,
            truncated=False,
            info={"target_action": self.target_action, "action": bounded, "step": float(self._step)},
        )


class ScalarLinearSystemEnv:
    """Scalar linear dynamical system: x_{t+1} = a * x_t + b * u_t + noise.

    Models a simplified LQR-style control problem. The agent must drive
    the state toward zero. Reward = -(x^2 + r * u^2) penalises both
    state deviation and control effort.

    This exercises temporal dynamics, unlike the stateless bandit environments.
    """

    def __init__(
        self,
        *,
        a: float = 1.0,
        b: float = 0.5,
        control_cost: float = 0.01,
        noise_std: float = 0.05,
        max_episode_steps: int = 20,
        seed: int = 42,
    ) -> None:
        self.spec = EnvSpec(
            env_id="scalar-linear-system-v0",
            observation_shape=(1,),
            action_shape=(1,),
            action_low=-1.0,
            action_high=1.0,
            reward_scale=1.0,
            max_episode_steps=max_episode_steps,
            metadata={"a": f"{a:.3f}", "b": f"{b:.3f}"},
        )
        self._a = float(a)
        self._b = float(b)
        self._control_cost = float(control_cost)
        self._noise_std = float(noise_std)
        self._rng = Random(seed)
        self._state = 0.0
        self._step = 0

    def reset(self) -> float:
        self._step = 0
        self._state = self._rng.uniform(-1.0, 1.0)
        return self._state

    def step(self, action: float) -> StepResult:
        self._step += 1
        bounded = max(self.spec.action_low, min(self.spec.action_high, float(action)))
        noise = self._rng.gauss(0.0, self._noise_std)
        self._state = self._a * self._state + self._b * bounded + noise
        self._state = max(-5.0, min(5.0, self._state))
        reward = -(self._state * self._state + self._control_cost * bounded * bounded)
        terminated = self._step >= self.spec.max_episode_steps
        truncated = abs(self._state) > 4.9
        return StepResult(
            observation=self._state,
            reward=reward,
            terminated=terminated,
            truncated=truncated,
            info={"state": self._state, "action": bounded, "step": float(self._step)},
        )


class NonlinearPendulumEnv:
    """Scalar inverted pendulum with simplified nonlinear dynamics.

    theta_{t+1} = theta_t + omega * dt
    omega_{t+1} = omega_t + (g/l * sin(theta) + u / (m*l^2)) * dt

    The observation is theta (angle), and the agent must keep it near zero.
    Reward = cos(theta) - 0.01 * u^2.
    """

    def __init__(
        self,
        *,
        dt: float = 0.05,
        max_episode_steps: int = 40,
        seed: int = 42,
    ) -> None:
        self.spec = EnvSpec(
            env_id="nonlinear-pendulum-v0",
            observation_shape=(1,),
            action_shape=(1,),
            action_low=-1.0,
            action_high=1.0,
            reward_scale=1.0,
            max_episode_steps=max_episode_steps,
            metadata={"dt": f"{dt:.3f}"},
        )
        self._dt = float(dt)
        self._g = 9.81
        self._l = 1.0
        self._m = 1.0
        self._rng = Random(seed)
        self._theta = 0.0
        self._omega = 0.0
        self._step = 0

    def reset(self) -> float:
        self._step = 0
        self._theta = self._rng.uniform(-0.3, 0.3)
        self._omega = self._rng.uniform(-0.1, 0.1)
        return self._theta

    def step(self, action: float) -> StepResult:
        self._step += 1
        u = max(self.spec.action_low, min(self.spec.action_high, float(action)))
        angular_accel = (self._g / self._l) * math.sin(self._theta) + u / (self._m * self._l * self._l)
        self._omega += angular_accel * self._dt
        self._omega = max(-5.0, min(5.0, self._omega))
        self._theta += self._omega * self._dt
        reward = math.cos(self._theta) - 0.01 * u * u
        terminated = self._step >= self.spec.max_episode_steps
        truncated = abs(self._theta) > math.pi
        return StepResult(
            observation=self._theta,
            reward=reward,
            terminated=terminated,
            truncated=truncated,
            info={"theta": self._theta, "omega": self._omega, "action": u, "step": float(self._step)},
        )
