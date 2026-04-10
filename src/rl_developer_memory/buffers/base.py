from __future__ import annotations

import random
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass


@dataclass(slots=True)
class Transition:
    """Transition record shared by replay and rollout buffers."""

    observation: float
    action: float
    reward: float
    next_observation: float
    done: bool


class ReplayBuffer(ABC):
    @abstractmethod
    def add(self, transition: Transition) -> None:
        ...

    @abstractmethod
    def sample(self) -> list[Transition]:
        ...

    @abstractmethod
    def clear(self) -> None:
        ...


class RolloutBuffer(ABC):
    @abstractmethod
    def add(self, transition: Transition) -> None:
        ...

    @abstractmethod
    def collect(self) -> list[Transition]:
        ...

    @abstractmethod
    def clear(self) -> None:
        ...


class InMemoryReplayBuffer(ReplayBuffer):
    """Small in-memory replay buffer with optional capacity and random sampling."""

    def __init__(self, *, capacity: int = 10_000) -> None:
        self._items: deque[Transition] = deque(maxlen=max(capacity, 1))

    def add(self, transition: Transition) -> None:
        self._items.append(transition)

    def sample(self, batch_size: int = 0) -> list[Transition]:
        if batch_size <= 0 or batch_size >= len(self._items):
            return list(self._items)
        return random.sample(list(self._items), batch_size)

    def clear(self) -> None:
        self._items.clear()

    def __len__(self) -> int:
        return len(self._items)


class InMemoryRolloutBuffer(RolloutBuffer):
    """Small in-memory rollout buffer for dependency-free tests."""

    def __init__(self) -> None:
        self._items: list[Transition] = []

    def add(self, transition: Transition) -> None:
        self._items.append(transition)

    def collect(self) -> list[Transition]:
        return list(self._items)

    def clear(self) -> None:
        self._items.clear()


class PrioritizedReplayBuffer(ReplayBuffer):
    """Proportional prioritized experience replay (dependency-free).

    Each transition has an associated priority.  Sampling probability is
    proportional to ``priority ^ alpha``.  Supports importance-sampling
    weight correction via ``beta`` annealing.
    """

    def __init__(self, *, capacity: int = 10_000, alpha: float = 0.6, beta: float = 0.4, beta_increment: float = 0.001) -> None:
        self._capacity = max(capacity, 1)
        self._alpha = float(alpha)
        self._beta = float(beta)
        self._beta_increment = float(beta_increment)
        self._items: list[Transition] = []
        self._priorities: list[float] = []
        self._max_priority = 1.0

    def add(self, transition: Transition, *, priority: float | None = None) -> None:
        p = float(priority) if priority is not None else self._max_priority
        if len(self._items) >= self._capacity:
            # Evict lowest-priority item
            min_idx = self._priorities.index(min(self._priorities))
            self._items[min_idx] = transition
            self._priorities[min_idx] = p
        else:
            self._items.append(transition)
            self._priorities.append(p)
        self._max_priority = max(self._max_priority, p)

    def sample(self, batch_size: int = 0) -> list[Transition]:  # type: ignore[override]
        if not self._items:
            return []
        if batch_size <= 0 or batch_size >= len(self._items):
            return list(self._items)
        # Compute sampling probabilities
        powered = [max(p, 1e-8) ** self._alpha for p in self._priorities]
        total = sum(powered)
        probs = [p / total for p in powered]
        # Weighted sampling without replacement
        indices = _weighted_sample(probs, batch_size)
        self._beta = min(1.0, self._beta + self._beta_increment)
        return [self._items[i] for i in indices]

    def sample_with_weights(self, batch_size: int) -> tuple[list[Transition], list[float], list[int]]:
        """Sample with IS weights and indices for priority updates."""
        if not self._items:
            msg = "Cannot sample from empty buffer"
            raise ValueError(msg)
        n = len(self._items)
        if batch_size >= n:
            batch_size = n
        powered = [max(p, 1e-8) ** self._alpha for p in self._priorities]
        total = sum(powered)
        probs = [p / total for p in powered]
        indices = _weighted_sample(probs, batch_size)
        self._beta = min(1.0, self._beta + self._beta_increment)
        # IS weights: (N * P(i))^(-beta) / max_weight
        weights = [(n * probs[i]) ** (-self._beta) for i in indices]
        max_w = max(weights) if weights else 1.0
        weights = [w / max_w for w in weights]
        return [self._items[i] for i in indices], weights, indices

    def update_priorities(self, indices: list[int], priorities: list[float]) -> None:
        for idx, p in zip(indices, priorities, strict=True):
            if 0 <= idx < len(self._priorities):
                self._priorities[idx] = abs(float(p)) + 1e-8
                self._max_priority = max(self._max_priority, self._priorities[idx])

    def clear(self) -> None:
        self._items.clear()
        self._priorities.clear()
        self._max_priority = 1.0

    def __len__(self) -> int:
        return len(self._items)


def _weighted_sample(probs: list[float], k: int) -> list[int]:
    """Weighted sampling without replacement (Efraimidis-Spirakis style)."""
    import math

    rng = random.Random()
    keys: list[tuple[float, int]] = []
    for i, p in enumerate(probs):
        u = rng.random()
        if u == 0.0:
            u = 1e-10
        key = math.log(u) / max(p, 1e-10)
        keys.append((key, i))
    keys.sort(reverse=True)
    return [idx for _, idx in keys[:k]]
