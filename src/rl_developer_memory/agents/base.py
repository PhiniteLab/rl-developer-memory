from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from rl_developer_memory.networks.base import ScalarPolicyNetwork, ScalarValueNetwork


@dataclass(slots=True)
class AgentContext:
    """Runtime context injected into the agent."""

    discount: float
    learning_rate: float
    entropy_temperature: float
    target_update_tau: float
    metadata: dict[str, str] = field(default_factory=dict)


class BaseAgent(ABC):
    @abstractmethod
    def act(self, observation: float) -> float:
        ...

    @abstractmethod
    def learn(self, *, observation: float, reward: float, next_observation: float, done: bool) -> dict[str, float]:
        ...

    @abstractmethod
    def update_target_network(self, *, tau: float | None = None) -> None:
        ...

    @abstractmethod
    def state_dict(self) -> dict[str, Any]:
        ...

    @abstractmethod
    def load_state_dict(self, state: dict[str, Any]) -> None:
        ...


class ActorCriticAgent(BaseAgent):
    """Scalar actor-critic agent with explicit objective hooks.

    The class intentionally exposes small methods so the theorem-to-code registry can bind
    Bellman, TD, actor, entropy, and target-update concepts to concrete code anchors.
    """

    def __init__(
        self,
        *,
        context: AgentContext,
        policy: ScalarPolicyNetwork | None = None,
        value: ScalarValueNetwork | None = None,
        target_value: ScalarValueNetwork | None = None,
    ) -> None:
        self.context = context
        self.policy = policy or ScalarPolicyNetwork(weight=0.0, bias=0.0)
        self.value = value or ScalarValueNetwork(weight=0.0, bias=0.0)
        self.target_value = target_value or ScalarValueNetwork(weight=self.value.weight, bias=self.value.bias)

    def act(self, observation: float) -> float:
        return max(-1.0, min(1.0, self.policy(observation)))

    def compute_td_target(self, reward: float, next_value: float, done: bool) -> float:
        return float(reward) if done else float(reward) + self.context.discount * float(next_value)

    def compute_bellman_residual(self, prediction: float, td_target: float) -> float:
        return float(td_target) - float(prediction)

    def compute_critic_objective(self, prediction: float, td_target: float) -> float:
        residual = self.compute_bellman_residual(prediction, td_target)
        return residual * residual

    def compute_actor_objective(self, action: float, advantage: float) -> float:
        return -float(action) * float(advantage)

    def compute_entropy_temperature_loss(self, entropy: float, target_entropy: float) -> float:
        return self.context.entropy_temperature * (float(target_entropy) - float(entropy))

    def learn(self, *, observation: float, reward: float, next_observation: float, done: bool) -> dict[str, float]:
        current_value = self.value(observation)
        next_value = self.target_value(next_observation)
        td_target = self.compute_td_target(reward, next_value, done)
        residual = self.compute_bellman_residual(current_value, td_target)
        policy_action = self.act(observation)
        actor_objective = self.compute_actor_objective(policy_action, residual)

        self.value.weight += self.context.learning_rate * residual * observation
        self.value.bias += self.context.learning_rate * residual
        self.policy.weight -= self.context.learning_rate * actor_objective * observation
        self.policy.bias -= self.context.learning_rate * actor_objective

        return {
            "td_target": td_target,
            "bellman_residual": residual,
            "critic_objective": self.compute_critic_objective(current_value, td_target),
            "actor_objective": actor_objective,
            "entropy_temperature": self.compute_entropy_temperature_loss(abs(policy_action), 0.5),
        }

    def update_target_network(self, *, tau: float | None = None) -> None:
        tau = self.context.target_update_tau if tau is None else float(tau)
        self.target_value.weight = (1.0 - tau) * self.target_value.weight + tau * self.value.weight
        self.target_value.bias = (1.0 - tau) * self.target_value.bias + tau * self.value.bias

    def state_dict(self) -> dict[str, Any]:
        return {
            "policy": self.policy.state_dict(),
            "value": self.value.state_dict(),
            "target_value": self.target_value.state_dict(),
            "context": {
                "discount": self.context.discount,
                "learning_rate": self.context.learning_rate,
                "entropy_temperature": self.context.entropy_temperature,
                "target_update_tau": self.context.target_update_tau,
                "metadata": dict(self.context.metadata),
            },
        }

    def load_state_dict(self, state: dict[str, Any]) -> None:
        self.policy.load_state_dict(state["policy"])
        self.value.load_state_dict(state["value"])
        self.target_value.load_state_dict(state["target_value"])
