from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(slots=True, frozen=True)
class AssumptionSpec:
    assumption_id: str
    description: str
    validator_anchor: str


@dataclass(slots=True, frozen=True)
class NotationSpec:
    symbol: str
    meaning: str
    code_anchor: str


@dataclass(slots=True, frozen=True)
class ObjectiveTerm:
    term_id: str
    equation_family: str
    description: str
    code_anchor: str


@dataclass(slots=True, frozen=True)
class RiskMetricBinding:
    metric_key: str
    theoretical_risk: str
    monitor_anchor: str


@dataclass(slots=True, frozen=True)
class TheoremMapping:
    mapping_id: str
    theorem_family: str
    equation_family: str
    code_anchor: str
    assumption_ids: tuple[str, ...]
    validator_anchor: str
    metric_keys: tuple[str, ...]
    risk_description: str


@dataclass(slots=True, frozen=True)
class TheoryRegistry:
    assumptions: tuple[AssumptionSpec, ...]
    notation: tuple[NotationSpec, ...]
    objectives: tuple[ObjectiveTerm, ...]
    mappings: tuple[TheoremMapping, ...]
    risk_metrics: tuple[RiskMetricBinding, ...]


def build_default_theory_registry() -> TheoryRegistry:
    assumptions = (
        AssumptionSpec("markov_transition", "Transitions satisfy the Markov property at the chosen observation boundary.", "rl_developer_memory.theory.registry.validate_assumption_bindings"),
        AssumptionSpec("bounded_reward", "Rewards are bounded and scaled before unstable updates accumulate.", "rl_developer_memory.theory.registry.validate_assumption_bindings"),
        AssumptionSpec("differentiable_policy", "The policy objective is differentiable under the chosen actor parameterization.", "rl_developer_memory.theory.registry.validate_assumption_bindings"),
        AssumptionSpec("stationary_rollout", "Rollout data comes from a controlled, seed-tracked policy regime.", "rl_developer_memory.theory.registry.validate_assumption_bindings"),
        AssumptionSpec("lyapunov_candidate_documented", "Stability claims identify the Lyapunov or surrogate energy function explicitly.", "rl_developer_memory.theory.registry.validate_assumption_bindings"),
        AssumptionSpec("observation_sufficiency", "The chosen observation interface is sufficient for the control or RL update being optimized.", "rl_developer_memory.theory.registry.validate_assumption_bindings"),
        AssumptionSpec("replay_distribution_matched", "Replay data remains close enough to the target policy distribution for the selected backup.", "rl_developer_memory.theory.registry.validate_assumption_bindings"),
        AssumptionSpec("control_objective_well_posed", "The control objective, constraints, and reward shaping encode a well-posed optimization problem.", "rl_developer_memory.theory.registry.validate_assumption_bindings"),
        AssumptionSpec("target_network_lag_controlled", "Target-network lag is controlled strongly enough to prevent unstable target drift.", "rl_developer_memory.theory.registry.validate_assumption_bindings"),
        AssumptionSpec("terminal_boundary_condition_documented", "HJB- or value-boundary-style claims document their terminal or boundary condition assumptions.", "rl_developer_memory.theory.registry.validate_assumption_bindings"),
    )
    notation = (
        NotationSpec("s_t", "State or observation at time t.", "rl_developer_memory.envs.base.StepResult.observation"),
        NotationSpec("a_t", "Action emitted by the policy at time t.", "rl_developer_memory.agents.base.ActorCriticAgent.act"),
        NotationSpec("r_t", "Reward observed after executing a_t.", "rl_developer_memory.envs.base.StepResult.reward"),
        NotationSpec("V_theta", "Value function parameterized by theta.", "rl_developer_memory.networks.base.ScalarValueNetwork"),
        NotationSpec("pi_theta", "Policy parameterized by theta.", "rl_developer_memory.networks.base.ScalarPolicyNetwork"),
    )
    objectives = (
        ObjectiveTerm("bellman_residual", "bellman", "Difference between critic target and current value prediction.", "rl_developer_memory.agents.base.ActorCriticAgent.compute_bellman_residual"),
        ObjectiveTerm("td_target", "temporal_difference", "Bootstrapped critic target used by off-policy and actor-critic methods.", "rl_developer_memory.agents.base.ActorCriticAgent.compute_td_target"),
        ObjectiveTerm("critic_objective", "critic_loss", "Squared Bellman residual used to train the critic.", "rl_developer_memory.agents.base.ActorCriticAgent.compute_critic_objective"),
        ObjectiveTerm("actor_objective", "policy_loss", "Policy objective driven by the current advantage estimate.", "rl_developer_memory.agents.base.ActorCriticAgent.compute_actor_objective"),
        ObjectiveTerm("entropy_temperature", "entropy_regularization", "Entropy/temperature term used to stabilize exploration.", "rl_developer_memory.agents.base.ActorCriticAgent.compute_entropy_temperature_loss"),
        ObjectiveTerm("advantage_estimator", "gae_like", "Advantage signal used to couple actor and critic updates.", "rl_developer_memory.trainers.pipeline.TrainerPipeline.compute_advantage_estimate"),
        ObjectiveTerm("lyapunov_hook", "stability_audit", "Audit hook for Lyapunov or stability-style claims.", "rl_developer_memory.trainers.pipeline.TrainerPipeline.run_stability_audit"),
        ObjectiveTerm("hjb_hook", "hjb_residual", "Audit hook for HJB-style residual checks in control-oriented updates.", "rl_developer_memory.trainers.pipeline.TrainerPipeline.run_hjb_audit"),
        ObjectiveTerm("constraint_hook", "constraint_barrier", "Audit hook for control-constraint margin checks.", "rl_developer_memory.trainers.pipeline.TrainerPipeline.run_constraint_audit"),
    )
    mappings = (
        TheoremMapping(
            mapping_id="bellman_residual",
            theorem_family="bellman_consistency",
            equation_family="bellman",
            code_anchor="rl_developer_memory.agents.base.ActorCriticAgent.compute_bellman_residual",
            assumption_ids=("markov_transition", "bounded_reward"),
            validator_anchor="rl_developer_memory.theory.registry.validate_assumption_bindings",
            metric_keys=("bellman_residual_abs_mean",),
            risk_description="Unbounded Bellman residuals indicate critic drift or target leakage.",
        ),
        TheoremMapping(
            mapping_id="td_target",
            theorem_family="temporal_difference",
            equation_family="temporal_difference",
            code_anchor="rl_developer_memory.agents.base.ActorCriticAgent.compute_td_target",
            assumption_ids=("markov_transition", "bounded_reward"),
            validator_anchor="rl_developer_memory.theory.registry.validate_assumption_bindings",
            metric_keys=("td_target_mean",),
            risk_description="TD targets drift when bootstrapping or reward scaling are inconsistent.",
        ),
        TheoremMapping(
            mapping_id="actor_objective",
            theorem_family="policy_gradient",
            equation_family="policy_loss",
            code_anchor="rl_developer_memory.agents.base.ActorCriticAgent.compute_actor_objective",
            assumption_ids=("differentiable_policy", "stationary_rollout"),
            validator_anchor="rl_developer_memory.theory.registry.validate_assumption_bindings",
            metric_keys=("actor_objective_mean",),
            risk_description="Large actor objectives correlate with unstable policy improvement.",
        ),
        TheoremMapping(
            mapping_id="critic_objective",
            theorem_family="actor_critic",
            equation_family="critic_loss",
            code_anchor="rl_developer_memory.agents.base.ActorCriticAgent.compute_critic_objective",
            assumption_ids=("bounded_reward",),
            validator_anchor="rl_developer_memory.theory.registry.validate_assumption_bindings",
            metric_keys=("critic_objective_mean",),
            risk_description="Critic objective spikes indicate unstable value learning.",
        ),
        TheoremMapping(
            mapping_id="entropy_temperature",
            theorem_family="maximum_entropy",
            equation_family="entropy_regularization",
            code_anchor="rl_developer_memory.agents.base.ActorCriticAgent.compute_entropy_temperature_loss",
            assumption_ids=("differentiable_policy",),
            validator_anchor="rl_developer_memory.theory.registry.validate_assumption_bindings",
            metric_keys=("entropy_temperature",),
            risk_description="Entropy collapse can cause premature exploitation and narrow policy support.",
        ),
        TheoremMapping(
            mapping_id="advantage_estimator",
            theorem_family="advantage_estimation",
            equation_family="gae_like",
            code_anchor="rl_developer_memory.trainers.pipeline.TrainerPipeline.compute_advantage_estimate",
            assumption_ids=("stationary_rollout",),
            validator_anchor="rl_developer_memory.theory.registry.validate_assumption_bindings",
            metric_keys=("advantage_abs_mean",),
            risk_description="Noisy advantages amplify actor update variance.",
        ),
        TheoremMapping(
            mapping_id="lyapunov_hook",
            theorem_family="stability_audit",
            equation_family="lyapunov_like",
            code_anchor="rl_developer_memory.trainers.pipeline.TrainerPipeline.run_stability_audit",
            assumption_ids=("lyapunov_candidate_documented",),
            validator_anchor="rl_developer_memory.theory.registry.validate_assumption_bindings",
            metric_keys=("lyapunov_margin",),
            risk_description="Missing or negative Lyapunov margins indicate unsafe control updates.",
        ),
        TheoremMapping(
            mapping_id="hjb_hook",
            theorem_family="hjb_optimality",
            equation_family="hjb_residual",
            code_anchor="rl_developer_memory.trainers.pipeline.TrainerPipeline.run_hjb_audit",
            assumption_ids=("control_objective_well_posed", "terminal_boundary_condition_documented"),
            validator_anchor="rl_developer_memory.theory.registry.validate_assumption_bindings",
            metric_keys=("hjb_residual_abs_mean",),
            risk_description="Large HJB residual proxies indicate control-optimality drift or inconsistent value targets.",
        ),
        TheoremMapping(
            mapping_id="constraint_hook",
            theorem_family="constraint_satisfaction",
            equation_family="constraint_barrier",
            code_anchor="rl_developer_memory.trainers.pipeline.TrainerPipeline.run_constraint_audit",
            assumption_ids=("control_objective_well_posed", "stationary_rollout"),
            validator_anchor="rl_developer_memory.theory.registry.validate_assumption_bindings",
            metric_keys=("constraint_margin_mean",),
            risk_description="Constraint margins near zero indicate safety or feasibility erosion.",
        ),
    )
    risk_metrics = (
        RiskMetricBinding("bellman_residual_abs_mean", "critic_drift", "rl_developer_memory.experiments.metrics.MetricsCollector.summary"),
        RiskMetricBinding("td_target_mean", "bootstrap_bias", "rl_developer_memory.experiments.metrics.MetricsCollector.summary"),
        RiskMetricBinding("actor_objective_mean", "policy_instability", "rl_developer_memory.experiments.metrics.MetricsCollector.summary"),
        RiskMetricBinding("advantage_abs_mean", "variance_explosion", "rl_developer_memory.experiments.metrics.MetricsCollector.summary"),
        RiskMetricBinding("entropy_temperature", "exploration_collapse", "rl_developer_memory.experiments.metrics.MetricsCollector.summary"),
        RiskMetricBinding("lyapunov_margin", "stability_regression", "rl_developer_memory.experiments.metrics.MetricsCollector.summary"),
        RiskMetricBinding("hjb_residual_abs_mean", "optimality_regression", "rl_developer_memory.experiments.metrics.MetricsCollector.summary"),
        RiskMetricBinding("constraint_margin_mean", "constraint_erosion", "rl_developer_memory.experiments.metrics.MetricsCollector.summary"),
    )
    return TheoryRegistry(assumptions=assumptions, notation=notation, objectives=objectives, mappings=mappings, risk_metrics=risk_metrics)


def validate_assumption_bindings(available_assumptions: Iterable[str], required_assumptions: Iterable[str]) -> list[str]:
    available = set(available_assumptions)
    missing = [item for item in required_assumptions if item not in available]
    return missing
