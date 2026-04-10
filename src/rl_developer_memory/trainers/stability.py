from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from rl_developer_memory.agents.base import BaseAgent
from rl_developer_memory.utils.numeric_guards import (
    NumericGuardResult,
    UpdateGuardResult,
    apply_gradient_clip,
    detect_exploding_update,
    is_finite_number,
)


@dataclass(slots=True)
class RunningNormalizer:
    """Running mean/std normalizer for scalar observations or rewards."""

    enabled: bool = True
    epsilon: float = 1e-8
    clip_range: float = 5.0
    count: int = 0
    mean: float = 0.0
    m2: float = 0.0

    def update(self, value: float) -> None:
        if not self.enabled:
            return
        normalized = float(value)
        if not is_finite_number(normalized):
            return
        self.count += 1
        delta = normalized - self.mean
        self.mean += delta / self.count
        delta2 = normalized - self.mean
        self.m2 += delta * delta2

    @property
    def variance(self) -> float:
        if self.count < 2:
            return 1.0
        return max(self.m2 / max(self.count - 1, 1), self.epsilon)

    def normalize(self, value: float, *, update: bool = True) -> float:
        if not self.enabled:
            return float(value)
        if not is_finite_number(float(value)):
            return float(value)
        normalized = (float(value) - self.mean) / (self.variance**0.5 + self.epsilon)
        if update:
            self.update(value)
        return max(-self.clip_range, min(self.clip_range, normalized))

    def state_dict(self) -> dict[str, float | int | bool]:
        return {
            "enabled": self.enabled,
            "epsilon": self.epsilon,
            "clip_range": self.clip_range,
            "count": self.count,
            "mean": self.mean,
            "m2": self.m2,
        }

    def load_state_dict(self, state: dict[str, Any]) -> None:
        self.enabled = bool(state.get("enabled", self.enabled))
        self.epsilon = float(state.get("epsilon", self.epsilon))
        self.clip_range = float(state.get("clip_range", self.clip_range))
        self.count = int(state.get("count", self.count))
        self.mean = float(state.get("mean", self.mean))
        self.m2 = float(state.get("m2", self.m2))


class RewardNormalizer(RunningNormalizer):
    """Reward scaling and normalization hook."""


class ObservationNormalizer(RunningNormalizer):
    """Observation normalization hook."""


@dataclass(slots=True, frozen=True)
class ControlledUpdate:
    name: str
    guard: NumericGuardResult
    explosion: UpdateGuardResult


@dataclass(slots=True)
class UpdateController:
    """Apply common scalar update controls before trainer commits a step."""

    max_norm: float
    ratio_threshold: float
    absolute_threshold: float
    reference_scale: float = 1.0

    def control(self, name: str, update: float) -> ControlledUpdate:
        clip_guard = apply_gradient_clip(update, max_norm=self.max_norm)
        explosion = detect_exploding_update(
            clip_guard.clipped_update,
            reference_scale=self.reference_scale,
            ratio_threshold=self.ratio_threshold,
            absolute_threshold=self.absolute_threshold,
        )
        self.reference_scale = max(abs(clip_guard.clipped_update), 1e-8)
        return ControlledUpdate(name=name, guard=clip_guard, explosion=explosion)


class TargetUpdatePolicy(ABC):
    """Strategy abstraction for target-network synchronization."""

    @abstractmethod
    def apply(self, agent: BaseAgent, *, step: int) -> dict[str, float]:
        ...


@dataclass(slots=True)
class SoftTargetUpdatePolicy(TargetUpdatePolicy):
    tau: float

    def apply(self, agent: BaseAgent, *, step: int) -> dict[str, float]:
        agent.update_target_network(tau=self.tau)
        return {"target_update_applied": 1.0, "target_update_tau": float(self.tau), "target_update_step": float(step)}


@dataclass(slots=True)
class HardTargetUpdatePolicy(TargetUpdatePolicy):
    interval: int

    def apply(self, agent: BaseAgent, *, step: int) -> dict[str, float]:
        if step % max(self.interval, 1) == 0:
            agent.update_target_network(tau=1.0)
            applied = 1.0
        else:
            applied = 0.0
        return {"target_update_applied": applied, "target_update_tau": 1.0 if applied else 0.0, "target_update_step": float(step)}


@dataclass(slots=True)
class EntropyTemperatureController:
    """Bounded entropy/temperature tuning hook."""

    initial_temperature: float
    min_temperature: float
    max_temperature: float
    learning_rate: float
    target_entropy: float
    enabled: bool = True
    current_temperature: float = field(init=False)

    def __post_init__(self) -> None:
        self.current_temperature = float(self.initial_temperature)

    def update(self, observed_entropy: float) -> float:
        if not self.enabled:
            return self.current_temperature
        delta = self.learning_rate * (self.target_entropy - float(observed_entropy))
        self.current_temperature = max(self.min_temperature, min(self.max_temperature, self.current_temperature + delta))
        return self.current_temperature

    def state_dict(self) -> dict[str, float | bool]:
        return {
            "initial_temperature": self.initial_temperature,
            "min_temperature": self.min_temperature,
            "max_temperature": self.max_temperature,
            "learning_rate": self.learning_rate,
            "target_entropy": self.target_entropy,
            "enabled": self.enabled,
            "current_temperature": self.current_temperature,
        }

    def load_state_dict(self, state: dict[str, Any]) -> None:
        self.enabled = bool(state.get("enabled", self.enabled))
        self.current_temperature = float(state.get("current_temperature", self.current_temperature))


@dataclass(slots=True)
class PlateauDetector:
    patience: int
    min_delta: float
    history: list[float] = field(default_factory=list)

    def update(self, value: float) -> bool:
        self.history.append(float(value))
        if len(self.history) < max(self.patience, 2):
            return False
        recent = self.history[-self.patience :]
        return max(recent) - min(recent) <= self.min_delta


@dataclass(slots=True)
class EarlyStoppingController:
    plateau_detector: PlateauDetector
    max_anomalies: int = 1
    anomaly_count: int = 0

    def register_anomaly(self) -> None:
        self.anomaly_count += 1

    def should_stop(self, *, latest_return: float, plateau: bool | None = None) -> bool:
        plateau_detected = self.plateau_detector.update(latest_return) if plateau is None else plateau
        return plateau_detected or self.anomaly_count >= self.max_anomalies
