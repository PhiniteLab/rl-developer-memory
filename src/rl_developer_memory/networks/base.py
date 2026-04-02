from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(slots=True, frozen=True)
class NetworkSpec:
    """Network description used by algorithm specs and config."""

    name: str
    role: str
    hidden_sizes: tuple[int, ...] = ()
    activation: str = "identity"
    output_activation: str = "identity"
    metadata: dict[str, str] = field(default_factory=dict)


class PolicyNetwork(Protocol):
    def __call__(self, observation: float) -> float:
        ...

    def state_dict(self) -> dict[str, float]:
        ...

    def load_state_dict(self, state: dict[str, float]) -> None:
        ...


class ValueNetwork(Protocol):
    def __call__(self, observation: float) -> float:
        ...

    def state_dict(self) -> dict[str, float]:
        ...

    def load_state_dict(self, state: dict[str, float]) -> None:
        ...


class _ScalarLinearModel:
    """Small scalar model used to keep the RL backbone executable without torch."""

    def __init__(self, *, weight: float = 0.0, bias: float = 0.0) -> None:
        self.weight = float(weight)
        self.bias = float(bias)

    def __call__(self, observation: float) -> float:
        return self.weight * float(observation) + self.bias

    def state_dict(self) -> dict[str, float]:
        return {"weight": self.weight, "bias": self.bias}

    def load_state_dict(self, state: dict[str, float]) -> None:
        self.weight = float(state["weight"])
        self.bias = float(state["bias"])


class ScalarPolicyNetwork(_ScalarLinearModel):
    """Deterministic scalar policy network for tests and smoke runs."""


class ScalarValueNetwork(_ScalarLinearModel):
    """Deterministic scalar value network for tests and smoke runs."""
