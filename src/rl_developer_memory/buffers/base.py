from __future__ import annotations

from abc import ABC, abstractmethod
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
    """Small in-memory replay buffer for dependency-free tests."""

    def __init__(self) -> None:
        self._items: list[Transition] = []

    def add(self, transition: Transition) -> None:
        self._items.append(transition)

    def sample(self) -> list[Transition]:
        return list(self._items)

    def clear(self) -> None:
        self._items.clear()


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
