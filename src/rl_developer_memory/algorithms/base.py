from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

DEFAULT_TRAINING_FLOW: tuple[str, ...] = (
    "problem/env definition",
    "observation/action interface",
    "model/network setup",
    "loss/objective definition",
    "theorem/equation integration",
    "training loop",
    "stabilization mechanisms",
    "evaluation/test",
    "failure analysis",
    "improvement loop",
)


@dataclass(slots=True, frozen=True)
class AlgorithmSpec:
    """Framework-agnostic algorithm contract used by the RL backbone."""

    name: str
    family: str
    policy_style: str
    data_strategy: str
    required_network_roles: tuple[str, ...]
    objective_terms: tuple[str, ...]
    stabilization_stack: tuple[str, ...]
    training_flow: tuple[str, ...] = DEFAULT_TRAINING_FLOW
    notes: str = ""


class BaseAlgorithm(ABC):
    """Minimal interface implemented by algorithm blueprints or adapters."""

    def __init__(self, spec: AlgorithmSpec) -> None:
        self.spec = spec

    @abstractmethod
    def build_networks(self) -> dict[str, str]:
        """Return the required network roles for the algorithm."""

    @abstractmethod
    def build_objectives(self) -> dict[str, str]:
        """Return a human-readable objective decomposition."""

    @abstractmethod
    def stabilization_hooks(self) -> tuple[str, ...]:
        """Return the stabilization hooks expected by the algorithm."""

    def to_dict(self) -> dict[str, Any]:
        """Serialize the algorithm contract for docs, tests, or manifests."""

        return {
            "name": self.spec.name,
            "family": self.spec.family,
            "policy_style": self.spec.policy_style,
            "data_strategy": self.spec.data_strategy,
            "required_network_roles": list(self.spec.required_network_roles),
            "objective_terms": list(self.spec.objective_terms),
            "stabilization_stack": list(self.spec.stabilization_stack),
            "training_flow": list(self.spec.training_flow),
            "notes": self.spec.notes,
        }
