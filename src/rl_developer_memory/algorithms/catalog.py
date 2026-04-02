from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .base import AlgorithmSpec, BaseAlgorithm


@dataclass(slots=True, frozen=True)
class AlgorithmBlueprint:
    """A thin, executable-facing contract for an algorithm family."""

    spec: AlgorithmSpec
    theorem_mapping_ids: tuple[str, ...]
    checkpoint_fields: tuple[str, ...]
    evaluation_focus: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "spec": {
                "name": self.spec.name,
                "family": self.spec.family,
                "policy_style": self.spec.policy_style,
                "data_strategy": self.spec.data_strategy,
                "required_network_roles": list(self.spec.required_network_roles),
                "objective_terms": list(self.spec.objective_terms),
                "stabilization_stack": list(self.spec.stabilization_stack),
                "training_flow": list(self.spec.training_flow),
                "notes": self.spec.notes,
            },
            "theorem_mapping_ids": list(self.theorem_mapping_ids),
            "checkpoint_fields": list(self.checkpoint_fields),
            "evaluation_focus": list(self.evaluation_focus),
        }


class _BlueprintAlgorithm(BaseAlgorithm):
    def build_networks(self) -> dict[str, str]:
        return {role: role for role in self.spec.required_network_roles}

    def build_objectives(self) -> dict[str, str]:
        return {term: term.replace("_", " ") for term in self.spec.objective_terms}

    def stabilization_hooks(self) -> tuple[str, ...]:
        return self.spec.stabilization_stack


def build_algorithm_catalog() -> dict[str, AlgorithmBlueprint]:
    """Return the supported algorithm blueprint catalog.

    The repo intentionally keeps these as lightweight contracts rather than binding
    to a specific DL backend. The training backbone can consume the same catalog
    regardless of whether the concrete implementation is scalar-test, NumPy, or torch.
    """

    common_checkpoint_fields = ("policy", "value", "optimizer", "metrics", "theory_bindings")
    return {
        "dqn": AlgorithmBlueprint(
            spec=AlgorithmSpec(
                name="DQN",
                family="value_based",
                policy_style="epsilon_greedy",
                data_strategy="off_policy_replay",
                required_network_roles=("q_network", "target_q_network"),
                objective_terms=("td_target", "bellman_residual"),
                stabilization_stack=("target_network", "gradient_clipping", "reward_scaling", "nan_guard"),
                notes="Discrete control template with target-network updates and replay.",
            ),
            theorem_mapping_ids=("td_target", "bellman_residual"),
            checkpoint_fields=common_checkpoint_fields,
            evaluation_focus=("return_mean", "bellman_residual_abs_mean", "crash_rate"),
        ),
        "ppo": AlgorithmBlueprint(
            spec=AlgorithmSpec(
                name="PPO",
                family="policy_gradient",
                policy_style="stochastic_policy",
                data_strategy="on_policy_rollout",
                required_network_roles=("policy_network", "value_network"),
                objective_terms=("actor_objective", "critic_objective", "advantage_estimator", "entropy_temperature"),
                stabilization_stack=("advantage_scaling", "entropy_tuning", "gradient_clipping", "early_stop"),
                notes="On-policy actor-critic template with clipped objectives and GAE-like advantages.",
            ),
            theorem_mapping_ids=("actor_objective", "critic_objective", "advantage_estimator", "entropy_temperature"),
            checkpoint_fields=common_checkpoint_fields,
            evaluation_focus=("return_mean", "advantage_abs_mean", "entropy_temperature"),
        ),
        "a2c": AlgorithmBlueprint(
            spec=AlgorithmSpec(
                name="A2C",
                family="policy_gradient",
                policy_style="stochastic_policy",
                data_strategy="on_policy_rollout",
                required_network_roles=("policy_network", "value_network"),
                objective_terms=("actor_objective", "critic_objective", "advantage_estimator"),
                stabilization_stack=("reward_scaling", "gradient_clipping", "nan_guard"),
                notes="Synchronous actor-critic template with explicit value baseline.",
            ),
            theorem_mapping_ids=("actor_objective", "critic_objective", "advantage_estimator"),
            checkpoint_fields=common_checkpoint_fields,
            evaluation_focus=("return_mean", "advantage_abs_mean"),
        ),
        "ddpg": AlgorithmBlueprint(
            spec=AlgorithmSpec(
                name="DDPG",
                family="actor_critic",
                policy_style="deterministic_policy",
                data_strategy="off_policy_replay",
                required_network_roles=("actor_network", "critic_network", "target_actor_network", "target_critic_network"),
                objective_terms=("actor_objective", "critic_objective", "td_target"),
                stabilization_stack=("target_network", "gradient_clipping", "action_clamp", "nan_guard"),
                notes="Deterministic actor-critic template with soft target updates.",
            ),
            theorem_mapping_ids=("actor_objective", "critic_objective", "td_target"),
            checkpoint_fields=common_checkpoint_fields,
            evaluation_focus=("return_mean", "td_target_mean", "control_effort"),
        ),
        "td3": AlgorithmBlueprint(
            spec=AlgorithmSpec(
                name="TD3",
                family="actor_critic",
                policy_style="deterministic_policy",
                data_strategy="off_policy_replay",
                required_network_roles=("actor_network", "critic_network_a", "critic_network_b", "target_actor_network", "target_critic_network_a", "target_critic_network_b"),
                objective_terms=("actor_objective", "critic_objective", "td_target"),
                stabilization_stack=("target_network", "delayed_policy_update", "target_smoothing", "gradient_clipping"),
                notes="Twin-critic deterministic template with delayed policy updates.",
            ),
            theorem_mapping_ids=("actor_objective", "critic_objective", "td_target"),
            checkpoint_fields=common_checkpoint_fields,
            evaluation_focus=("return_mean", "td_target_mean", "constraint_violation_rate"),
        ),
        "sac": AlgorithmBlueprint(
            spec=AlgorithmSpec(
                name="SAC",
                family="actor_critic",
                policy_style="stochastic_policy",
                data_strategy="off_policy_replay",
                required_network_roles=("actor_network", "critic_network_a", "critic_network_b", "target_critic_network_a", "target_critic_network_b"),
                objective_terms=("actor_objective", "critic_objective", "td_target", "entropy_temperature"),
                stabilization_stack=("target_network", "entropy_tuning", "reward_scaling", "gradient_clipping", "nan_guard"),
                notes="Entropy-regularized actor-critic template suitable for continuous control.",
            ),
            theorem_mapping_ids=("actor_objective", "critic_objective", "td_target", "entropy_temperature"),
            checkpoint_fields=common_checkpoint_fields,
            evaluation_focus=("return_mean", "entropy_temperature", "crash_rate"),
        ),
    }
