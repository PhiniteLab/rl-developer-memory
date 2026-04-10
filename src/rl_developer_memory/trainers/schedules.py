"""Learning-rate and exploration schedules for the RL training pipeline."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Learning rate schedules
# ---------------------------------------------------------------------------


class LRSchedule(ABC):
    """Base class for learning-rate schedules."""

    @abstractmethod
    def get_lr(self, step: int) -> float:
        ...


@dataclass(slots=True)
class ConstantLR(LRSchedule):
    """Constant learning rate (no decay)."""

    lr: float

    def get_lr(self, step: int) -> float:
        return self.lr


@dataclass(slots=True)
class LinearDecayLR(LRSchedule):
    """Linearly decay from *initial_lr* to *final_lr* over *total_steps*."""

    initial_lr: float
    final_lr: float
    total_steps: int

    def get_lr(self, step: int) -> float:
        if self.total_steps <= 0:
            return self.initial_lr
        progress = min(float(step) / float(self.total_steps), 1.0)
        return self.initial_lr + (self.final_lr - self.initial_lr) * progress


@dataclass(slots=True)
class CosineAnnealingLR(LRSchedule):
    """Cosine annealing from *initial_lr* to *final_lr* over *total_steps*."""

    initial_lr: float
    final_lr: float
    total_steps: int

    def get_lr(self, step: int) -> float:
        if self.total_steps <= 0:
            return self.initial_lr
        progress = min(float(step) / float(self.total_steps), 1.0)
        cosine_decay = 0.5 * (1.0 + math.cos(math.pi * progress))
        return self.final_lr + (self.initial_lr - self.final_lr) * cosine_decay


@dataclass(slots=True)
class ExponentialDecayLR(LRSchedule):
    """Exponentially decay by *decay_rate* every *decay_steps*."""

    initial_lr: float
    decay_rate: float
    decay_steps: int
    min_lr: float = 0.0

    def get_lr(self, step: int) -> float:
        if self.decay_steps <= 0:
            return self.initial_lr
        exponent = float(step) / float(self.decay_steps)
        return max(self.initial_lr * (self.decay_rate ** exponent), self.min_lr)


@dataclass(slots=True)
class WarmupLR(LRSchedule):
    """Linear warmup for *warmup_steps*, then delegate to *base_schedule*."""

    warmup_steps: int
    base_schedule: LRSchedule

    def get_lr(self, step: int) -> float:
        if step < self.warmup_steps and self.warmup_steps > 0:
            warmup_lr = self.base_schedule.get_lr(0) * (float(step + 1) / float(self.warmup_steps))
            return warmup_lr
        return self.base_schedule.get_lr(step - self.warmup_steps)


# ---------------------------------------------------------------------------
# Exploration schedules
# ---------------------------------------------------------------------------


class ExplorationSchedule(ABC):
    """Base class for exploration parameter schedules (e.g., epsilon-greedy)."""

    @abstractmethod
    def get_epsilon(self, step: int) -> float:
        ...


@dataclass(slots=True)
class LinearEpsilonDecay(ExplorationSchedule):
    """Linearly anneal epsilon from *start* to *end* over *decay_steps*."""

    start: float = 1.0
    end: float = 0.01
    decay_steps: int = 1000

    def get_epsilon(self, step: int) -> float:
        if self.decay_steps <= 0:
            return self.end
        progress = min(float(step) / float(self.decay_steps), 1.0)
        return self.start + (self.end - self.start) * progress


@dataclass(slots=True)
class ExponentialEpsilonDecay(ExplorationSchedule):
    """Exponentially decay epsilon: start * decay_rate^(step / decay_steps)."""

    start: float = 1.0
    end: float = 0.01
    decay_rate: float = 0.995
    decay_steps: int = 1

    def get_epsilon(self, step: int) -> float:
        exponent = float(step) / max(float(self.decay_steps), 1.0)
        return max(self.start * (self.decay_rate ** exponent), self.end)


__all__ = [
    "ConstantLR",
    "CosineAnnealingLR",
    "ExplorationSchedule",
    "ExponentialDecayLR",
    "ExponentialEpsilonDecay",
    "LRSchedule",
    "LinearDecayLR",
    "LinearEpsilonDecay",
    "WarmupLR",
]
